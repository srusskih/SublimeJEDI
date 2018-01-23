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
	$(call get_dependency,jedi,https://github.com/davidhalter/jedi,v0.11.1)
	$(call get_dependency,parso,https://github.com/davidhalter/parso,v0.1.1)

clean:
	rm -rf SublimeJEDI.sublime-package
	find -name "*.pyc" -exec rm {} \;

# will build a sublime package
build: clean
	zip -r SublimeJEDI.sublime-package `ls` -x .git SublimeJEDI.sublime-package *.pyc
