"""Where do essays go when an attack changes the official verdict? (a small follow-up to notebook 22b, for the "Re-run the trial" panel)

    python scripts/jury_flip_destinations.py

Reads results/22b_attack_juror_logits.csv (scores of the 1,373 attacked essays, no text) and results/22_juror_scores.csv (calibration), and for every
group and attack counts the essays whose official zone changed, by (zone before -> zone after). Writes results/22b_flip_destinations.csv.
It uses the same ensemble as the API (src/jury.Calibration) and refuses to overwrite.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.jury import Calibration, zone_of

out = ROOT / "results" / "22b_flip_destinations.csv"
if out.exists():
    sys.exit(f"{out} exists; refusing to overwrite")
cal = Calibration()
lg = pd.read_csv(ROOT / "results" / "22b_attack_juror_logits.csv")
p_ens, _ = cal.official(lg[["s42", "s43", "s44"]].to_numpy())
lg["zone"] = zone_of(p_ens)
before = lg[lg["attack"] == "original"].set_index("row_id")["zone"]
rows = []
for (group, attack), d in lg[lg["attack"] != "original"].groupby(["group", "attack"], sort=False):
    d = d.set_index("row_id")
    pair = pd.DataFrame({"before": before.loc[d.index], "after": d["zone"]})
    for (b, a), n in pair.value_counts().items():
        rows.append({"group": group, "attack": attack, "zone_before": b, "zone_after": a, "essays": int(n), "group_size": len(d)})
pd.DataFrame(rows).to_csv(out, index=False)
print("wrote", out, len(rows), "rows")
