#!/usr/bin/env bash

# Kill processes running on ixa pipe ports as configured in ./run_nlpws.sh
# (port numbers are copied here too)

pidfile="./pidfile"

tokport=2020
posport=2040
posportalt=3040
parseport=2080
srlport=5007


if [[ ! -f "$pidfile" ]]; then
  tokpid=$(netstat -tnlp|grep $tokport | perl -pe "s/.+:$tokport.+\s([0-9]+)\/java/\1/")
  pospid=$(netstat -tnlp|grep $posport | perl -pe "s/.+:$posport.+\s([0-9]+)\/java/\1/")
  pospidalt=$(netstat -tnlp|grep $posportalt | perl -pe "s/.+:$posportalt.+\s([0-9]+)\/java/\1/")
  parsepid=$(netstat -tnlp|grep $parseport | perl -pe "s/.+:$parseport.+\s([0-9]+)\/java/\1/")
  srlpid=$(netstat -tnlp|grep $srlport | perl -pe "s/.+:$srlport.+\s([0-9]+)\/java/\1/")
  kill $tokpid
  kill $pospid
  kill $pospidalt
  kill $parsepid
  kill $srlpid
  exit
fi

for p in $(cat $pidfile); do
  kill -9 $p > /dev/null &> /dev/null
done
