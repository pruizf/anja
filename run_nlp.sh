#!/usr/bin/env bash

# Runs ixa pipes spanish modules on $indir, writes results to $outdir
# Uses the server setups (starts the servers if needed)

# Author: Pablo Ruiz
# Date: 2016-08-19
# e-mail: pabloruizfabo@gmail.com


tokport=2020
posport=2040
posportalt=3040
parseport=2080
srlport=5007  # hardcoded in ixa-pipe-srl

pidfile="./pidfile"
batchlog="./batchlog"

usage(){
  echo -e "Usage:\n  $(basename $0) input_dir output_dir postagger_type(def|alt) [only_deps]"
  echo -e "  postagger_type can only be 'def' or 'alt'"
  echo -e "  Leave 'only_deps' blank if want to get SRL results besides dependency parsing"
  exit
}


# IO

indir="$1"
outdir="$2"
postype="$3"  # "def", "alt" for alternative pos-tagger
onlydeps="$4"

[[ "$1" = "-h" ]] && usage

if [ ! -z "$4" ]; then
    deps_or_srl="only-deps"
  else
    deps_or_srl=""
fi

if [ ! -d "$outdir" ]; then
  echo "- Creating dir: [$outdir]"
  mkdir -p "$outdir"
fi

[[ "$postype" != "def" && "$postype" != "alt" ]] && usage


# Pipes
pipesdir=/home/pablo/usr/local/ixa-servers
tokdir="$pipesdir/ixa-pipe-tok"
posdir="$pipesdir/ixa-pipe-pos"
posdiralt="$pipesdir/ixa-pipe-altpos"
parsedir="$pipesdir/ixa-pipe-parse"
srldir="$pipesdir/ixa-pipe-srl-3/IXA-EHU-srl"

# Models
posmodel="$posdir/morph-models-1.5.0/es/es-pos-perceptron-autodict01-ancora-2.0.bin"
lemmodel="$posdir/morph-models-1.5.0/es/es-lemma-perceptron-ancora-2.0.bin"
posmodelalt="$posdiralt/pos-models-1.4.0/es/es-maxent-100-c5-baseline-autodict01-ancora.bin"
parsemodel="$parsedir/parse-models/es-parser-chunking.bin"
# srl module gives deps and srl
srlmodel="$srldir/IXA-EHU-srl/target/models/spa/srl-spa.model"

# Jars
tokjar="$tokdir/target/ixa-pipe-tok-1.8.5-exec.jar"
posjar="$posdir/target/ixa-pipe-pos-1.5.1-exec.jar"
posjaralt="$posdiralt/target/ixa-pipe-pos-1.4.6.jar"
parsejar="$parsedir/target/ixa-pipe-parse-1.1.2.jar"
srljar="$srldir/target/IXA-EHU-srl-3.0.jar"


# Start servers if needed

#[[ -f "$pidfile" ]] && rm "$pidfile"
[[ -f "$batchlog" ]] && rm "$batchlog"

# tok
if [[ -z $(netstat -tlnp | grep ":$tokport") ]] ; then
  java -jar "$tokjar" server -l es -p "$tokport" >> "$batchlog" 2>&1 &
  echo $! >> "$pidfile"
  echo "Started tokenizer server on $tokport"
fi
# pos
if [[ "$postype" = "alt" ]]; then
  posport="$posportalt"
  posjar="$posjaralt"
fi
if [[ -z $(netstat -tlnp | grep ":$posport") ]] ; then
  if [[ "$postype" = "def" ]]; then
      java -jar "$posjar" server -l es -p "$posport" -m "$posmodel" \
      -lm "$lemmodel" >> "$batchlog" 2>&1 &
    elif [[ "$postype" = "alt" ]]; then
      java -jar "$posjar" server -l es -p "$posport" -m "$posmodelalt" \
      >> "$batchlog" 2>&1 &
    else usage
  fi
  echo $! >> "$pidfile"
  while [[ -z $(grep -P "listening to port $posport" "$batchlog") ]]; do
    echo -n "*"
    sleep 1
  done
  echo -e "\nStarted tagger server on $posport"
fi
# parse
if [[ -z $(netstat -tlnp | grep ":$parseport") ]] ; then
  java -jar "$parsejar" server -l es -p "$parseport" -m "$parsemodel" >> \
  "$batchlog" 2>&1 &
  echo $! >> "$pidfile"
  while [[ -z $(grep -P "listening to port $parseport" "$batchlog") ]]; do
    echo -n "*"
    sleep 1
  done
  echo -e "\nStarted parser server on $parseport"
fi
# srl
if [[ -z $(netstat -tlnp | grep ":$srlport") ]] ; then
  java -cp "$srljar" ixa.srl.SRLServer es >> "$batchlog" 2>&1 &
  echo $! >> "$pidfile"
  echo "Started SRL server on $srlport"
  echo -n "* Waiting to load SRL "
  while [[ -z $(grep -P "Listening port $srlport" "$batchlog") ]]; do
    echo -n "."
    sleep 3
  done
  echo -e " [DONE]"
fi

# run
for fn in $(find "$indir" -type f) ; do
  if [ ! -s "$fn" ] ; then
    echo -e "\n SKIPPING EMPTY FILE [$fn]\n" | tee -a "$batchlog"
    continue
  fi
  echo "- Parsing $fn" | tee -a "$batchlog"
  # renaming works differently according to the corpus
  #outfn="$outdir/$(echo $(basename $fn)| sed -e 's/.txt/_parsed.xml/g')"
  #outfn="$outdir/$(echo $(basename $fn)| sed -e 's/\(_oneline\)\{0,1\}.txt/_parsed.xml/')"
  outfn="$outdir/$(echo $(basename $fn)| sed -e 's/\(.txt_oneline\)\{0,1\}.txt/_parsed.xml/')"
  cat "$fn" | java -jar "$tokjar" client -p "$tokport" | \
              java -jar "$posjar" client -p "$posport" | \
              java -jar "$parsejar" client -p "$parseport" | \
              java -Xms2500m -cp "$srljar" ixa.srl.SRLClient es "$deps_or_srl" > \
              "$outfn" 2>> "$batchlog"
  echo "- OUT $outfn" | tee -a "$batchlog"
done

# keep last 4 pids only
echo "$(tac $pidfile | head -n 4)" > "$pidfile"
