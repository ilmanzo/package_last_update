#!/bin/bash
#osc my packages
# wait 1 sec between requests
for p in $(osc -A https://api.opensuse.org my packages | cut -d '/' -f 2) ; do sleep 1 && ./last_update.py $p ;done
