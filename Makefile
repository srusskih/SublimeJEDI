define get_dependency =
	git clone $(2) dep
	cd dep; git checkout $(3)
	mv dep/$(1) dependencies/
	rm -rf dep
endef


dummy:
	exit 0

dependencies:
	rm -rf dependencies/
	mkdir dependencies/
	$(call get_dependency,jedi,https://github.com/davidhalter/jedi,v0.12.1)
	$(call get_dependency,parso,https://github.com/davidhalter/parso,v0.3.1)

clean:
	find . -name '*.pyc' -delete

# will build a sublime package
build: clean
	zip -r SublimeJEDI.sublime-package `ls` -x .git SublimeJEDI.sublime-package *.pyc


dev_install_mac:
	ln -s "${PWD}" ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/
