#!/bin/sh
for p in $(osc my packages | cut -d '/' -f 2) ; do ./last_update $p ; done
