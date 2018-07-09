packer = 7z
pack = $(packer) a -mx=9
arcx = .7z
docs = COPYING Changelog README.md
basename = photomv
zipname = $(basename).zip
arcname = $(basename)$(arcx)
srcarcname = $(basename)-src$(arcx)
backupdir = ~/shareddocs/pgm/python/

app:
	$(pack) -tzip $(zipname) __main__.py photomv.py pmvcommon.py pmvconfig.py pmvtemplates.py pmvmetadata.py pmvui.py pmvgtkui.py pmvtermui.py
	@echo '#!/usr/bin/env python3' >$(basename)
	@cat $(zipname) >>$(basename)
	rm $(zipname)
	chmod 755 $(basename)

archive:
	$(pack) $(srcarcname) *.py *. Makefile *.geany do_commit $(docs)
distrib:
	make app
	$(pack) $(basename)-$(shell python3 -c 'from pmvcommon import VERSION; print(VERSION)')$(arcx) $(basename) $(docs)
backup:
	make archive
	mv $(srcarcname) $(backupdir)
update:
	$(packer) x -y $(backupdir)$(srcarcname)
commit:
	git commit -a -uno -m "$(shell python3 -c 'from pmvcommon import VERSION; print(VERSION)')"
docview:
	$(eval docname = README.htm)
	@echo "<html><head><meta charset="utf-8"><title>$(shell python3 -c 'from pmvcommon import TITLE_VERSION; print(TITLE_VERSION)') README</title></head><body>" >$(docname)
	markdown_py README.md >>$(docname)
	@echo "</body></html>" >>$(docname)
	x-www-browser $(docname)
	#rm $(docname)
