"""src/jury.py without a web server: the scale, the zones, the official verdict, and (with a GPU) that the serving copies reproduce
the logits saved in Phase 1."""
import math

import numpy as np
import pandas as pd
import pytest

from src import jury as core

ROOT = core.ROOT


@pytest.fixture(scope="module")
def cal():
    return core.Calibration()


def test_the_scale_has_its_lines_in_the_declared_places(cal):
    s = cal.scale()
    assert s["val_humans"] == 2291
    assert s["flag_line"] == pytest.approx(-math.log10(0.00235)) and s["above_usual_line"] == pytest.approx(-math.log10(0.01032))
    assert s["cap"] == pytest.approx(math.log10(2292)) and 1.9 < s["above_usual_line"] < s["flag_line"] < s["cap"]


def test_zone_boundaries_are_inclusive_at_tau():
    z = core.zone_of([0.00235, 0.002351, 0.01032, 0.010321, 1.0])
    assert list(z) == ["flagged", "above_usual", "above_usual", "not_flagged", "not_flagged"]


def test_a_score_above_every_validation_student_is_at_the_end_of_the_scale(cal):
    top = max(cal.val[42])
    m = cal.mark(42, top + 1.0)
    assert m["at_cap"] and m["p"] == pytest.approx(1 / 2292) and m["position"] == pytest.approx(cal.cap) and m["zone"] == "flagged"
    low = cal.mark(42, min(cal.val[42]) - 1.0)
    assert low["p"] == 1.0 and low["position"] == 0.0 and low["zone"] == "not_flagged" and not low["at_cap"]


def test_the_flag_line_is_the_fifth_highest_validation_student_for_every_juror(cal):
    for seed in core.SEEDS:
        v = np.sort(cal.val[seed])[::-1]
        assert cal.mark(seed, np.nextafter(v[4], np.inf))["zone"] == "flagged"     # strictly above the 5th highest: at most 4 students score higher
        assert cal.mark(seed, v[4])["zone"] != "flagged"                           # the 5th highest itself is not flagged


def test_the_official_verdict_reproduces_notebook_20_on_every_held_out_essay(cal):
    h = pd.read_csv(ROOT / "results" / "20_heldout_scores.csv")
    p_ens, _ = cal.official(h[["logit_s42", "logit_s43", "logit_s44"]].to_numpy())
    mine = core.zone_of(p_ens)
    theirs = h["zone_A"].replace({"cannot tell": "above_usual", "not flagged": "not_flagged"}).to_numpy()
    assert len(h) == 9856 and (mine == theirs).all()


def test_verdict_has_three_seeds_and_a_zone(cal):
    v = cal.verdict([9.8, 9.8, 9.8])
    assert v["zone"] == "flagged" and [s["seed"] for s in v["seeds"]] == [42, 43, 44] and all(s["zone"] == "flagged" for s in v["seeds"])
    assert cal.verdict([-8.0, -8.0, -8.0])["zone"] == "not_flagged"


def test_summary_counts_and_changes(cal):
    same = {s: np.array([9.8, 9.8]) for s in core.SEEDS}
    out = core.summary(cal, same, with_before=True)
    assert out["counts"] == {"flagged": 20, "above_usual": 0, "not_flagged": 0} and out["jurors_changed_zone"] == 0 and not out["official_changed"]
    moved = {s: np.array([9.8, -8.0]) for s in core.SEEDS}
    out = core.summary(cal, moved, with_before=True)
    assert out["counts"]["not_flagged"] == 20 and out["before"]["says_ai"] == 20 and out["jurors_changed_zone"] == 20 and out["official_changed"]


def test_trial_events_come_in_seed_order_then_one_summary():
    class J:
        tokenizer = None
        def tokenise(self, texts): return list(texts)
        def logits_of(self, seed, ids): return np.array([9.8] * len(ids), dtype=np.float32)
    events = list(core.trial(J(), core.Calibration(), "an essay"))
    assert [e["type"] for e in events] == ["juror"] * 20 + ["summary"] and [e["seed"] for e in events[:20]] == core.SEEDS and "before" not in events[0]
    with_typos = list(core.trial(J(), core.Calibration(), "an essay", edited="an essya"))
    assert "before" in with_typos[0] and with_typos[-1]["jurors_changed_zone"] == 0


torch = pytest.importorskip("torch")


@pytest.mark.skipif(not torch.cuda.is_available() or not (core.FP16_DIR / "s61").exists(), reason="needs the GPU and models/jury_fp16")
def test_serving_copies_reproduce_the_saved_phase_1_logits_and_zones(cal):
    from src.data import load_splits
    d = load_splits("val", "test")
    saved = pd.read_csv(core.SCORES_CSV).set_index("row_id")
    ids = np.random.default_rng(3).choice(d.index.to_numpy(), 8, replace=False)
    served = core.Jury().score_many(d.loc[ids, "text"].tolist(), [42, 50, 61])
    ref = saved.loc[ids, ["s42", "s50", "s61"]].to_numpy()
    assert np.abs(served - ref).max() < 0.05
    for c, seed in enumerate([42, 50, 61]):
        assert (core.zone_of(cal.p(seed, served[:, c])) == core.zone_of(cal.p(seed, ref[:, c]))).all()
