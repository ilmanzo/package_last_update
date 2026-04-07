#!/bin/bash
export PYTHONWARNINGS="ignore"
#osc my packages
# wait 1 sec between requests
for p in $(osc -A https://api.opensuse.org my packages | cut -d '/' -f 2) ; do ./last_update.py $p ; sleep 1;done
