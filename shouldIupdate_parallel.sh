#!/bin/bash
#osc my packages

if ! command -v osc &> /dev/null; then
  echo "Error: The 'osc' command is not available. Please install it and try again later."
  exit 1
fi

if ! command -v parallel &> /dev/null ; then
  echo "GNU parallel not found, please install it before running this script"
  exit 1
fi

packages=$(osc -A https://api.opensuse.org my packages 2>&1)

if [[ "$packages" == *Name\ or\ service\ not\ known* ]]; then
  echo "Unable to connect to the specified API URL. Please check the URL and your network connection."
  exit 2
fi

echo "$packages" | cut -d '/' -f 2 | parallel -j 2 './last_update.py'

