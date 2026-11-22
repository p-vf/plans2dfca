#!/bin/bash

domain=$1
problem=$2
planfolder=$3

mkdir -p $3
mv sas_plan* $3 2>/dev/null || true

all_plans=$(grep -rnwl $3 -e '')
valid_plans=$(grep -rnwl $3 -e '(unit cost)' -e '(general cost)')

#echo $all_plans
#echo $valid_plans

num_invalid_plans=$(expr $(echo $all_plans | wc -w) - $(echo $valid_plans | wc -w))

echo "Number of broken plans: $num_invalid_plans"

### COMPARE ALL PLANS
plan_file_hashes=()
NUM_IDENTICAL_PLANS=0

for f in $valid_plans; do
  cur_hash="$(sha1sum $f | grep -o "^\w*\b")"
  if [[ " ${plan_file_hashes[*]} " =~ " ${cur_hash} " ]]; then
    ((NUM_IDENTICAL_PLANS = NUM_IDENTICAL_PLANS + 1))
  fi
  plan_file_hashes+=($cur_hash)
done

#echo ${plan_file_hashes[@]}
echo "Number of identical plans: $NUM_IDENTICAL_PLANS"

### VALIDATE ALL PLANS

VAL_OUT=$(validate -S $domain $problem $valid_plans)
EXITCODE_VAL=$?

VAL_OUT=$(echo $VAL_OUT | tr -d '\r' | tr -d "\n")
VAL_OUT=$(echo $VAL_OUT | sed 's/failed/-1 /g')

echo "Plan costs: [$VAL_OUT]"

exit $(($NUM_IDENTICAL_PLANS > $EXITCODE_VAL ? 1 : $EXITCODE_VAL))
