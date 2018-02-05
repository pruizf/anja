#!/usr/bin/env bash

# Splits golden set and results by type, to run neleval by type

# Usage: ./eval_per_type.sh [golden|any_other_word] \
#                           system_results \
#                           directory_to_output_system_results_split_by_type \
#                           directory_to_output_evaluation_metrics
#                           [run_id_to_append_to_evaluation_metrics_file]
#
# Options
#   [golden]: Give this as 1st arg to create the split golden set, if it's already available
#             you can write anything else as the 1st argument.
#   [run_id_to_append_to_evaluation_metrics_file]: Give a 5th argument if want a new name
#                                                  for the results file (otherwise appends
#                                                  to default name, see below).


refres=""     # e.g. "./ref/ref_sonnets-norm_sto-sorted.txt"
refbytype=""  # output of create_typed_results


# system
sysres="$2"
sysbytype="$3"
outdir="$4"
runid="$5"

# create output dirs and filenames
if [ ! -d "$sysbytype" ]; then
  mkdir -p "$sysbytype"
fi

if [ ! -z "$4" ] && [ ! -d "$outdir" ]; then
  mkdir -p "$outdir"
fi

if [ -z "$5" ]; then
    myrunid="summary_by_type"
  else
    myrunid="summary_by_type_$runid"
fi

# get types
sysrestypes=$(cut -f4 "$sysres" | sort | uniq)
golrestypes=$(cut -f4 "$refres" | sort | uniq)

# create output files
#   create golden split only if asked for
if [ "$1" = "golden" ]; then
    for gtype in $golrestypes; do
      grep -P "\t$gtype\t" "$refres" > "$refbytype/$gtype"
    done
fi


#   create system split, always
for rtype in $sysrestypes; do
  #echo "SYS $rtype"
  grep -P "\t$rtype\t" "$sysres" > "$sysbytype/$rtype"
  # create empty files in golden when system outputs a non-golden type
  if [ ! -f "$refbytype/$rtype" ]; then
    echo "### Creating empty golden file for type [$rtype]"
    touch "$refbytype/$rtype"
  fi
done

# evaluate
#   dedup results type labels first
alltypes="$sysrestypes\n$golrestypes"
alluniq=$(echo -e "$alltypes" | sort | uniq)

#   run neleval
echo -e "\n$myrunid\n" >> "$outdir/$myrunid"
echo -e "etype\tptp\tfp\trtp\tfn\tprecis\trecall\tfscore\tmeasure"
echo -e "etype\tptp\tfp\trtp\tfn\tprecis\trecall\tfscore\tmeasure" >> \
        "$outdir/$myrunid"

for ufn in $alluniq; do
  if [ ! -f "$sysbytype/$ufn" ]; then
    # get false negative count
    fncount=$(wc -l "$refbytype/$ufn" | cut -d' ' -f1)
    outl="$ufn\t0\t0\t0\t$fncount\t0.0000\t0.0000\t0.0000\tstrong_typed_mention_match"
    echo -e $outl
    echo -e $outl >> "$outdir/$myrunid"
    continue
  fi
  mm4type=$(./nel evaluate -g "$refbytype/$ufn" "$sysbytype/$ufn" 2> /dev/null | \
            grep -P "(strong_typed_mention_match)")
  echo -e "$ufn\t$mm4type"
  echo -e "$ufn\t$mm4type" >> "$outdir/$myrunid"
done
