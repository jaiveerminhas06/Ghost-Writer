#!/usr/bin/env bash
# Phase 1 of the jury: train the 17 new jurors (seeds 45-61), notebook 08 recipe, full training set, one after another.
# Restartable at any time: a seed whose model folder exists is skipped (train_variant.py never overwrites).
#   nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --why="Ghost Writer jury" bash scripts/jury_train.sh >> results/22_jury_train.log 2>&1 &
# Guards, checked before EVERY seed:
#   - the charger must be connected (on battery the GPU runs ~40% slower and the battery drains): it waits, up to 6 hours, and logs it
#   - the GPU must be free (under 600 MiB in use): never train while the demo server or anything else holds it
# Override the seeds with SEEDS="45 46" bash scripts/jury_train.sh
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SEEDS="${SEEDS:-$(seq 45 61)}"
ts() { date '+%F %T'; }
on_battery() { for f in /sys/class/power_supply/BAT*/status; do [ -e "$f" ] && [ "$(cat "$f")" = "Discharging" ] && return 0; done; return 1; }
gpu_used_mib() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
echo "[$(ts)] === jury training started, seeds: $(echo $SEEDS) ==="
FAILED=0
for s in $SEEDS; do
  if [ -d "models/distilroberta_orig_s$s" ]; then echo "[$(ts)] seed $s: model exists, skipping"; continue; fi
  waited=0
  while on_battery; do
    [ $waited -eq 0 ] && echo "[$(ts)] seed $s: ON BATTERY, waiting for the charger"
    sleep 60; waited=$((waited + 60))
    if [ $waited -ge 21600 ]; then echo "[$(ts)] gave up waiting for the charger after 6 h"; exit 2; fi
  done
  used=$(gpu_used_mib)
  if [ "$used" -ge 600 ]; then echo "[$(ts)] seed $s: GPU busy ($used MiB in use), not training. Stop the other process and run this script again"; exit 3; fi
  echo "[$(ts)] seed $s: starting (battery: $(cat /sys/class/power_supply/BAT*/status 2>/dev/null | head -1), GPU in use: $used MiB)"
  python scripts/train_variant.py --variant baseline --full --seed "$s" \
    || { echo "[$(ts)] seed $s FAILED, retrying once"; sleep 20; python scripts/train_variant.py --variant baseline --full --seed "$s"; } \
    || { echo "[$(ts)] seed $s FAILED twice"; FAILED=1; }
done
echo "[$(ts)] === jury training finished, failed=$FAILED ==="
exit $FAILED
