#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Miscellaneous network utility code."""

from __future__ import absolute_import, division, with_statement

import errno
import os
import re
import socket
import stat
import sys

try:
    import ssl
except ImportError:
    ssl = None

from typhoon.ioloop import IOLoop
from typhoon.platform.auto import set_close_exec


def bind_sockets(port, address=None, family=socket.AF_UNSPEC, backlog=128, flags=None):
    """Creates listening sockets bound to the given port and address.

    Returns a list of socket objects (multiple sockets are returned if
    the given address maps to multiple IP addresses, which is most common
    for mixed IPv4 and IPv6 use).

    Address may be either an IP address or hostname.  If it's a hostname,
    the server will listen on all IP addresses associated with the
    name.  Address may be an empty string or None to listen on all
    available interfaces.  Family may be set to either `socket.AF_INET`
    or `socket.AF_INET6` to restrict to IPv4 or IPv6 addresses, otherwise
    both will be used if available.

    The ``backlog`` argument has the same meaning as for
    `socket.listen() <socket.socket.listen>`.

    ``flags`` is a bitmask of AI_* flags to `~socket.getaddrinfo`, like
    ``socket.AI_PASSIVE | socket.AI_NUMERICHOST``.
    """
    sockets = []
    if address == "":
        address = None
    if not socket.has_ipv6 and family == socket.AF_UNSPEC:
        # Python can be compiled with --disable-ipv6, which causes
        # operations on AF_INET6 sockets to fail, but does not
        # automatically exclude those results from getaddrinfo
        # results.
        # http://bugs.python.org/issue16208
        family = socket.AF_INET
    if flags is None:
        flags = socket.AI_PASSIVE
    for res in set(socket.getaddrinfo(address, port, family, socket.SOCK_STREAM,
                                      0, flags)):
        af, socktype, proto, canonname, sockaddr = res
        try:
            sock = socket.socket(af, socktype, proto)
        except socket.error:
            e = sys.exc_info()[1]
            if e.args[0] == errno.EAFNOSUPPORT:
                continue
            raise
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if af == socket.AF_INET6:
            # On linux, ipv6 sockets accept ipv4 too by default,
            # but this makes it impossible to bind to both
            # 0.0.0.0 in ipv4 and :: in ipv6.  On other systems,
            # separate sockets *must* be used to listen for both ipv4
            # and ipv6.  For consistency, always disable ipv4 on our
            # ipv6 sockets and use a separate ipv4 socket when needed.
            #
            # Python 2.x on windows doesn't have IPPROTO_IPV6.
            if hasattr(socket, "IPPROTO_IPV6") and \
                    hasattr(socket, "IPV6_V6ONLY"):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setblocking(0)
        sock.bind(sockaddr)
        sock.listen(backlog)
        sockets.append(sock)
    return sockets

if hasattr(socket, 'AF_UNIX'):
    def bind_unix_socket(file, mode=int('600', 8), backlog=128):
        """Creates a listening unix socket.

        If a socket with the given name already exists, it will be deleted.
        If any other file with that name exists, an exception will be
        raised.

        Returns a socket object (not a list of socket objects like
        `bind_sockets`)
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        set_close_exec(sock.fileno())
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        try:
            st = os.stat(file)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno != errno.ENOENT:
                raise
        else:
            if stat.S_ISSOCK(st.st_mode):
                os.remove(file)
            else:
                raise ValueError("File %s exists and is not a socket", file)
        sock.bind(file)
        os.chmod(file, mode)
        sock.listen(backlog)
        return sock


def add_accept_handler(sock, callback, io_loop=None):
    """Adds an `.IOLoop` event handler to accept new connections on ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    `.IOLoop` handlers.
    """
    if io_loop is None:
        io_loop = IOLoop.current()

    def accept_handler(fd, events):
        while True:
            try:
                connection, address = sock.accept()
            except socket.error:
                e = sys.exc_info()[1]
                # EWOULDBLOCK and EAGAIN indicate we have accepted every
                # connection that is available.
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                # ECONNABORTED indicates that there was a connection
                # but it was closed while still in the accept queue.
                # (observed on FreeBSD).
                if e.args[0] == errno.ECONNABORTED:
                    continue
                raise
            callback(connection, address)
    io_loop.add_handler(sock.fileno(), accept_handler, IOLoop.READ)


def is_valid_ip(ip):
    """Returns true if the given string is a well-formed IP address.

    Supports IPv4 and IPv6.
    """
    try:
        res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC,
                                 socket.SOCK_STREAM,
                                 0, socket.AI_NUMERICHOST)
        return bool(res)
    except socket.gaierror:
        e = sys.exc_info()[1]
        if e.args[0] == socket.EAI_NONAME:
            return False
        raise
    return True


# These are the keyword arguments to ssl.wrap_socket that must be translated
# to their SSLContext equivalents (the other arguments are still passed
# to SSLContext.wrap_socket).
_SSL_CONTEXT_KEYWORDS = frozenset(['ssl_version', 'certfile', 'keyfile',
                                   'cert_reqs', 'ca_certs', 'ciphers'])


def ssl_options_to_context(ssl_options):
    """Try to convert an ``ssl_options`` dictionary to an
    `~ssl.SSLContext` object.

    The ``ssl_options`` dictionary contains keywords to be passed to
    `ssl.wrap_socket`.  In Python 3.2+, `ssl.SSLContext` objects can
    be used instead.  This function converts the dict form to its
    `~ssl.SSLContext` equivalent, and may be used when a component which
    accepts both forms needs to upgrade to the `~ssl.SSLContext` version
    to use features like SNI or NPN.
    """
    if isinstance(ssl_options, dict):
        assert all(k in _SSL_CONTEXT_KEYWORDS for k in ssl_options), ssl_options
    if (not hasattr(ssl, 'SSLContext') or
            isinstance(ssl_options, ssl.SSLContext)):
        return ssl_options
    context = ssl.SSLContext(
        ssl_options.get('ssl_version', ssl.PROTOCOL_SSLv23))
    if 'certfile' in ssl_options:
        context.load_cert_chain(ssl_options['certfile'], ssl_options.get('keyfile', None))
    if 'cert_reqs' in ssl_options:
        context.verify_mode = ssl_options['cert_reqs']
    if 'ca_certs' in ssl_options:
        context.load_verify_locations(ssl_options['ca_certs'])
    if 'ciphers' in ssl_options:
        context.set_ciphers(ssl_options['ciphers'])
    return context


def ssl_wrap_socket(socket, ssl_options, server_hostname=None, **kwargs):
    """Returns an ``ssl.SSLSocket`` wrapping the given socket.

    ``ssl_options`` may be either a dictionary (as accepted by
    `ssl_options_to_context`) or an `ssl.SSLContext` object.
    Additional keyword arguments are passed to ``wrap_socket``
    (either the `~ssl.SSLContext` method or the `ssl` module function
    as appropriate).
    """
    context = ssl_options_to_context(ssl_options)
    if hasattr(ssl, 'SSLContext') and isinstance(context, ssl.SSLContext):
        if server_hostname is not None and getattr(ssl, 'HAS_SNI'):
            # Python doesn't have server-side SNI support so we can't
            # really unittest this, but it can be manually tested with
            # python3.2 -m typhoon.httpclient https://sni.velox.ch
            return context.wrap_socket(socket, server_hostname=server_hostname,
                                       **kwargs)
        else:
            return context.wrap_socket(socket, **kwargs)
    else:
        return ssl.wrap_socket(socket, **dict(context, **kwargs))

if hasattr(ssl, 'match_hostname') and hasattr(ssl, 'CertificateError'):  # python 3.2+
    ssl_match_hostname = ssl.match_hostname
    SSLCertificateError = ssl.CertificateError
else:
    # match_hostname was added to the standard library ssl module in python 3.2.
    # The following code was backported for older releases and copied from
    # https://bitbucket.org/brandon/backports.ssl_match_hostname
    class SSLCertificateError(ValueError):
        pass

    def _dnsname_to_pat(dn, max_wildcards=1):
        pats = []
        for frag in dn.split(r'.'):
            if frag.count('*') > max_wildcards:
                # Issue #17980: avoid denials of service by refusing more
                # than one wildcard per fragment.  A survery of established
                # policy among SSL implementations showed it to be a
                # reasonable choice.
                raise SSLCertificateError(
                    "too many wildcards in certificate DNS name: " + repr(dn))
            if frag == '*':
                # When '*' is a fragment by itself, it matches a non-empty dotless
                # fragment.
                pats.append('[^.]+')
            else:
                # Otherwise, '*' matches any dotless fragment.
                frag = re.escape(frag)
                pats.append(frag.replace(r'\*', '[^.]*'))
        return re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)

    def ssl_match_hostname(cert, hostname):
        """Verify that *cert* (in decoded format as returned by
        SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 rules
        are mostly followed, but IP addresses are not accepted for *hostname*.

        CertificateError is raised on failure. On success, the function
        returns nothing.
        """
        if not cert:
            raise ValueError("empty or no certificate")
        dnsnames = []
        san = cert.get('subjectAltName', ())
        for key, value in san:
            if key == 'DNS':
                if _dnsname_to_pat(value).match(hostname):
                    return
                dnsnames.append(value)
        if not dnsnames:
            # The subject is only checked when there is no dNSName entry
            # in subjectAltName
            for sub in cert.get('subject', ()):
                for key, value in sub:
                    # XXX according to RFC 2818, the most specific Common Name
                    # must be used.
                    if key == 'commonName':
                        if _dnsname_to_pat(value).match(hostname):
                            return
                        dnsnames.append(value)
        if len(dnsnames) > 1:
            raise SSLCertificateError("hostname %r "
                                      "doesn't match either of %s"
                                      % (hostname, ', '.join(map(repr, dnsnames))))
        elif len(dnsnames) == 1:
            raise SSLCertificateError("hostname %r "
                                      "doesn't match %r"
                                      % (hostname, dnsnames[0]))
        else:
            raise SSLCertificateError("no appropriate commonName or "
                                      "subjectAltName fields were found")
