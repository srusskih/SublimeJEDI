dummy:
	exit 0

_get_dependency:
	git clone $(REPO) dep
	cd dep; git checkout $(TAG)
	mv dep/$(TARGET) dependencies/
	rm -rf dep

.PHONY: dependencies
dependencies:
	rm -rf dependencies/
	mkdir dependencies/
	$(MAKE) _get_dependency -e REPO=https://github.com/davidhalter/jedi -e TAG=v0.13.3 -e TARGET=jedi
	$(MAKE) _get_dependency -e REPO=https://github.com/davidhalter/parso -e TAG=v0.4.0 -e TARGET=parso
	patch --dry-run -p0 < jedi_0.13.x.patch
	patch -p0 < jedi_0.13.x.patch

clean:
	find . -name '*.pyc' -delete

# will build a sublime package
build: clean
	zip -r SublimeJEDI.sublime-package `ls` -x .git SublimeJEDI.sublime-package *.pyc


dev_install_mac:
	ln -s "${PWD}" ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/
