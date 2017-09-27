packer = 7z
pack = $(packer) a -mx=9
arcx = .7z
docs = COPYING README.md
basename = photomv
zipname = $(basename).zip
arcname = $(basename)$(arcx)
srcarcname = $(basename)-src$(arcx)
backupdir = ~/shareddocs/pgm/python/

app:
	$(pack) -tzip $(zipname) __main__.py photomv.py pmvcommon.py pmvconfig.py pmvtemplates.py pmvmetadata.py
	@echo '#!/usr/bin/env python3' >$(basename)
	@cat $(zipname) >>$(basename)
	rm $(zipname)
	chmod 755 $(basename)

archive:
	$(pack) $(srcarcname) *.py *. Makefile *.geany do_commit $(docs)
distrib:
	$(pack) $(arcname) $(docs)
backup:
	make archive
	mv $(srcarcname) $(backupdir)
update:
	$(packer) x -y $(backupdir)$(srcarcname)
commit:
	./do_commit
