#!/bin/bash
#osc my packages
for p in $(osc -A https://api.opensuse.org my packages | cut -d '/' -f 2)
do 
  ./last_update $p &
done
wait
