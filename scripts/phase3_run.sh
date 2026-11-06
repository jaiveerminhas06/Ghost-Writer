#!/usr/bin/env bash
# Phase 3 runs, restartable at any time (finished folds are skipped).
#   bash scripts/phase3_run.sh "A B"                 # variants A then B on the seven pre-registered folds
#   bash scripts/phase3_run.sh "C"                   # only if A and B each lowered false flags (decision rule in 17_augment.ipynb)
#   FULL="A" bash scripts/phase3_run.sh ""            # train variant A on the whole training set, seeds 42 43 44, saving the models
# Time-boxed sessions: HOURS=1.5 bash scripts/phase3_run.sh "A B" starts no new fold unless it can finish before the time is up
# (a fold takes about 16 minutes), so you can run it for as long as the laptop stays on and carry on later; finished folds are kept.
# Recommended wrapper (keeps the laptop awake, logs to a file):
#   nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --why="Ghost Writer phase 3" bash scripts/phase3_run.sh "A B" >> results/17_variants/run.log 2>&1 &
# The seven folds are the pre-registered ones: the four worst prompts, the median, the two best (from the 16b results; see 17_augment.ipynb).
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FOLDS="${FOLDS:-11 4 3 6 7 12 2}"
mkdir -p results/17_variants results/17_final
run() {   # args for train_variant.py
  # a finished fold is skipped by the python script itself; only stop here before STARTING one that needs time
  if ! time_left; then STOPPED=1; return; fi
  python scripts/train_variant.py "$@" || { echo "[$(date '+%F %T')] FAILED: $*, retrying once"; sleep 20; python scripts/train_variant.py "$@"; } || { echo "[$(date '+%F %T')] FAILED twice: $*"; FAILED=1; }
}
FAILED=0
STOPPED=0
DEADLINE=0
[ -n "${HOURS:-}" ] && DEADLINE=$(python -c "import time,os;print(int(time.time()+float(os.environ['HOURS'])*3600))")
time_left() { [ "$DEADLINE" -eq 0 ] || [ $(( DEADLINE - $(date +%s) )) -gt 1000 ]; }   # more than ~17 minutes left (or no limit)
echo "[$(date '+%F %T')] === phase 3 run started: variants '$1', full '${FULL:-}' ==="
for v in $1; do for k in $FOLDS; do run --variant "$v" --fold "$k" --seed 42; done; done
for v in ${FULL:-}; do for s in 42 43 44; do run --variant "$v" --full --seed "$s"; done; done
[ "$STOPPED" -eq 1 ] && echo "[$(date '+%F %T')] time box reached: stopped before starting the next fold; run the same command again to continue"
echo "[$(date '+%F %T')] === phase 3 run finished, failed=$FAILED ==="
exit $FAILED
