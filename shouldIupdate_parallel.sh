#!/bin/bash
#osc my packages


if ! command -v osc &> /dev/null; then
  echo "Error: The 'osc' command is not available. Please install it and try again later."
  exit 1
fi

packages=$(osc -A https://api.opensuse.org my packages 2>&1)

if [[ "$packages" == *Name\ or\ service\ not\ known* ]]; then
  echo "Unable to connect to the specified API URL. Please check the URL and your network connection."
  exit 1
fi

for p in $(echo "$packages" | cut -d '/' -f 2)
do 
  ./last_update $p &
done
wait
