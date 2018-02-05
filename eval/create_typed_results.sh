#!/usr/bin/env bash

resset="$1"
restypes="$2"
resbytype="$3"

if [ ! -d "$resbytype" ]; then
  mkdir -p "$resbytype"
fi

for rtype in $(cat "$restypes"); do
  has_match=$(grep -P "\t$rtype\t" "$resset")
  if [ ! -z "$has_match" ];
    then
      echo "$has_match" > "$resbytype/$rtype"
    else
      touch "$resbytype/$rtype"
  fi
done
