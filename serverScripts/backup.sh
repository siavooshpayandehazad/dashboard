#!/bin/bash
today=$(date +"%d-%m-%y")
FILENAME=backup-journal-$today.tar.gz
SRCDIR=/media/pi/ec83d7d4-47dd-4b33-9fe9-261c1b6700fa/dashboard
DESDIR=/media/pi/770b5ec5-99c6-48f5-8b04-0e52526c5326/backups
rm $DESDIR/*.tar.gz
tar -cpzf $DESDIR/$FILENAME $SRCDIR
