#!/usr/bin/env bash
# The whole Phase 2b run, restartable at any time (finished folds are skipped):
#   nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --why="Ghost Writer LOPO run" bash scripts/lopo_run.sh >> results/16b_lopo/run.log 2>&1 &
# 13 folds with seed 42, then the median fold again with seeds 43 and 44 (seed-noise check). One python process per fold, so GPU
# memory is fully released between folds. A failed fold is retried once, then skipped; the script exits non-zero if any are missing.
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
run() {   # fold seed
  python scripts/lopo_fold.py --fold "$1" --seed "$2" || { echo "[$(date '+%F %T')] fold $1 seed $2 FAILED, retrying once"; sleep 20; python scripts/lopo_fold.py --fold "$1" --seed "$2"; } || { echo "[$(date '+%F %T')] fold $1 seed $2 FAILED twice"; FAILED=1; }
}
FAILED=0
echo "[$(date '+%F %T')] === LOPO run started ==="
for k in $(seq 0 12); do run "$k" 42; done
if FOLD=$(python scripts/lopo_pick_fold.py); then
  echo "[$(date '+%F %T')] seed-noise fold = $FOLD (left-out rate closest to the median)"
  for s in 43 44; do run "$FOLD" "$s"; done
else
  echo "[$(date '+%F %T')] cannot pick the seed-noise fold: $FOLD"; FAILED=1
fi
echo "[$(date '+%F %T')] === LOPO run finished, failed=$FAILED ==="
exit $FAILED
