dummy:
	exit 0

update_jedi:
	git clone https://github.com/davidhalter/jedi jedi_upstream
	cp -r jedi_upstream/jedi .
	rm -rf jedi_upstream
