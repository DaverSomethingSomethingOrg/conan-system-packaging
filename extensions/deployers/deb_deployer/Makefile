# Simple Makefile to faithfully copy the pre-installed full content of the
# current directory to DESTDIR, excluding our template's `Makefile` and
# `debian/`.
#
# Thanks to https://john-tucker.medium.com/debian-packaging-by-example-118c18f5dbfe
#

all:
	@echo 'Nothing to `make` here'

install:
	tar c --exclude Makefile --exclude debian --file - . | ( cd $(DESTDIR); tar xvf - )
