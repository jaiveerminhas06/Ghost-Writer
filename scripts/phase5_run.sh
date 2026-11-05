#!/usr/bin/env bash
# Phase 5 GPU jobs, restartable at any time (finished jobs are skipped by the python scripts), optionally time-boxed:
#   HOURS=1.5 bash scripts/phase5_run.sh        # no new job unless it can finish in time (a job takes 14-17 minutes)
# 1. the original recipe (notebook 08) trained on the whole training set with seeds 43 and 44 -> models/distilroberta_orig_s43, _s44
#    (seed 42 is the existing models/distilroberta_finetuned); val and test scores in results/17_final/orig_s*_scores.csv
# 2. leave-one-prompt-out fold 11 (Seeking multiple opinions), seeds 42 43 44, original recipe, with typo-perturbed scores of the left-out
#    essays -> results/19_phase5/lopo/ (the stability tests of notebook 19)
# Wrapper that keeps the laptop awake (and PLUG IN THE CHARGER: on battery the GPU runs ~40% slower and drains fast):
#   nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --why="Ghost Writer phase 5" bash scripts/phase5_run.sh >> results/19_phase5/run.log 2>&1 &
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p results/17_final results/19_phase5/lopo
DEADLINE=0
[ -n "${HOURS:-}" ] && DEADLINE=$(python -c "import time,os;print(int(time.time()+float(os.environ['HOURS'])*3600))")
time_left() { [ "$DEADLINE" -eq 0 ] || [ $(( DEADLINE - $(date +%s) )) -gt 1100 ]; }
FAILED=0; STOPPED=0
run() {   # script and args
  if ! time_left; then STOPPED=1; return; fi
  python "$@" || { echo "[$(date '+%F %T')] FAILED: $*, retrying once"; sleep 20; python "$@"; } || { echo "[$(date '+%F %T')] FAILED twice: $*"; FAILED=1; }
}
echo "[$(date '+%F %T')] === phase 5 run started ==="
for s in 43 44; do run scripts/train_variant.py --variant baseline --full --seed "$s"; done
for s in 42 43 44; do run scripts/lopo_fold_typos.py --fold 11 --seed "$s"; done
[ "$STOPPED" -eq 1 ] && echo "[$(date '+%F %T')] time box reached: run the same command again to continue"
echo "[$(date '+%F %T')] === phase 5 run finished, failed=$FAILED ==="
exit $FAILED
