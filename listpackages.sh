#!/bin/bash
#
MAINPROJECT=openSUSE:Factory
test -f packages.txt || osc --apiurl https://api.opensuse.org ls $MAINPROJECT > packages.txt
rm results.txt
for p in $(cat packages.txt); do
  echo $p
  osc --apiurl https://api.opensuse.org ls -l ${MAINPROJECT}/${p} | grep changes >> results.txt
done
