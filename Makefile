dummy:
	exit 0

update_jedi:
	rm -rf jedi
	git clone https://github.com/davidhalter/jedi jedi_upstream
	cp -r jedi_upstream/jedi .
	rm -rf jedi_upstream

clean:
	rm -rf SublimeJEDI.sublime-package
	find -name "*.pyc" -exec rm {} \;

# will build a sublime package
build: clean
	zip -r SublimeJEDI.sublime-package `ls` -x .git SublimeJEDI.sublime-package *.pyc
