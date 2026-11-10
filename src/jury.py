"""The Jury: twenty equally good detectors (seeds 42-61, same data and recipe) judge an essay one by one.

What lives here (no web code; api/ only calls this):
  Calibration   each juror's own 2,291 validation-human scores, from results/22_juror_scores.csv. A score becomes that juror's tail
                probability p, then a zone ("flagged" if p <= tau(1%), "above_usual" if p <= tau(5%), else "not_flagged").
  position(p)   -log10(p): the common scale the jury page draws on. It is the same place for every juror, whatever its raw logit range.
                It stops at log10(1 + n_val_humans) = 3.36: p cannot go below 1/(1+n), so the end of the scale means "scores higher than
                every student essay in validation", not a measurement.
  Jury          the 20 fp16 serving copies (models/jury_fp16/). They wait in CPU memory and each is moved to the GPU only while it scores.
  trial()       the generator behind POST /api/jury: one event per juror, then a summary. Optionally the essay is first given typos.
The official verdict is the three-seed ensemble (seeds 42-44, mean of p-values, re-calibrated: src/ensemble.PEnsemble) with the same
three zones. The thresholds are the pre-declared ones from notebook 18b; nothing is retuned here.
"""
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .conformal import tail_p
from .ensemble import PEnsemble

ROOT = Path(__file__).resolve().parent.parent
SEEDS = list(range(42, 62))
ENSEMBLE_SEEDS = (42, 43, 44)
TAU_FLAG, TAU_ABOVE = 0.00235, 0.01032          # tau(1%) and tau(5%), rule (d), notebook 18b; for single models and for the ensemble
FP16_DIR = ROOT / "models" / "jury_fp16"
SCORES_CSV = ROOT / "results" / "22_juror_scores.csv"
TYPO_RATE = 0.05
ZONES = ("flagged", "above_usual", "not_flagged")


def zone_of(p):
    """Zone for a tail probability (or an array of them)."""
    return np.where(np.asarray(p) <= TAU_FLAG, "flagged", np.where(np.asarray(p) <= TAU_ABOVE, "above_usual", "not_flagged"))


class Calibration:
    """Everything that turns a raw logit into a p, a zone and a position. Needs no model."""

    def __init__(self, scores_csv=SCORES_CSV):
        s = pd.read_csv(scores_csv)
        val_h = s[(s["split"] == "val") & (s["label"] == 0)]
        self.seeds = [c for c in (f"s{x}" for x in SEEDS) if c in val_h.columns]
        self.val = {int(c[1:]): np.sort(val_h[c].to_numpy(dtype=float)) for c in self.seeds}
        self.n = len(val_h)
        self.ens = PEnsemble(np.column_stack([val_h[f"s{x}"].to_numpy(dtype=float) for x in ENSEMBLE_SEEDS]))
        self.cap = math.log10(1 + self.n)            # position of p = 1/(1+n): scores above every validation student

    def p(self, seed, logits):
        return tail_p(np.asarray(logits, dtype=float), self.val[seed])

    def scale(self):
        """Positions of the two lines and the end of the scale, for the page."""
        return {"min": 0.0, "above_usual_line": -math.log10(TAU_ABOVE), "flag_line": -math.log10(TAU_FLAG), "cap": self.cap,
                "val_humans": self.n, "tau_flag": TAU_FLAG, "tau_above_usual": TAU_ABOVE}

    def position(self, p):
        return -np.log10(np.asarray(p, dtype=float))

    def official(self, logits_42_44):
        """The ensemble verdict for essays: array (n, 3) of the logits of seeds 42, 43, 44. Returns p_ens and the three seeds' p."""
        X = np.asarray(logits_42_44, dtype=float)
        return self.ens.p_ens(X), self.ens.p_seeds(X)

    def verdict(self, logits_42_44):
        """One essay's official verdict as the API reports it: zone, p, and each of the three seeds' own p and zone."""
        p_ens, p_seeds = self.official(np.asarray(logits_42_44, dtype=float).reshape(1, 3))
        return {"zone": str(zone_of(p_ens[0])), "p": float(p_ens[0]),
                "seeds": [{"seed": s, "p": float(p_seeds[0, i]), "zone": str(zone_of(p_seeds[0, i]))} for i, s in enumerate(ENSEMBLE_SEEDS)]}

    def mark(self, seed, logit):
        """One juror's mark: p, position on the common scale, zone, and whether it sits at the end of the scale."""
        p = float(self.p(seed, [logit])[0])
        return {"seed": seed, "p": p, "position": float(self.position(p)), "zone": str(zone_of(p)),
                "at_cap": bool(p <= 1.0 / (1 + self.n) + 1e-12), "ensemble_member": seed in ENSEMBLE_SEEDS}


# ---------------------------------------------------------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------------------------------------------------------
class Jury:
    """The serving copies. fp16 on the GPU (one resident model, weights swapped in); on a machine without one they are upcast to fp32 on the CPU (slow: about 1.3 s per juror per
    essay, so the live jury is meant for a GPU and the API refuses it elsewhere; the official verdict still works)."""

    def __init__(self, device=None, directory=FP16_DIR, max_len=512, lazy=None):
        """lazy=True (or the environment variable GW_JURY_LAZY=1) reads a juror from disk each time it is needed and keeps nothing: about
        3 GB less memory, slower per trial. The default keeps all twenty in memory."""
        import torch
        self.torch = torch
        self.lazy = bool(int(os.environ.get("GW_JURY_LAZY", "0"))) if lazy is None else lazy
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dir, self.max_len = Path(directory), max_len
        self.models = {}
        self._gpu = None
        self._tok = None

    @property
    def live(self):
        """True if a trial of all twenty jurors is practical (a GPU is present)."""
        return self.device == "cuda"

    @property
    def tokenizer(self):
        if self._tok is None:
            from transformers import AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(self.dir / "s42")
        return self._tok

    def _read(self, seed):
        """Juror `seed` from disk. GPU: its fp16 weights as a dict of CPU tensors; CPU: an fp32 model."""
        if self.device == "cuda":
            from safetensors.torch import load_file
            return load_file(str(self.dir / f"s{seed}" / "model.safetensors"))
        from transformers import AutoModelForSequenceClassification
        return AutoModelForSequenceClassification.from_pretrained(self.dir / f"s{seed}", dtype=self.torch.float32).eval()

    def _load(self, seed):
        """GPU: the juror's weights (fp16) are kept in pinned CPU memory. One model stays resident on the GPU and the weights of whichever
        juror is scoring are copied into it (about 40 ms), which is faster than moving 20 models back and forth.
        CPU: each juror is its own fp32 model. In lazy mode nothing is kept: the juror is read again every time."""
        if self.device == "cuda" and self._gpu is None:
            from transformers import AutoModelForSequenceClassification
            self._gpu = AutoModelForSequenceClassification.from_pretrained(self.dir / "s42", dtype=self.torch.float16).cuda().eval()
        if self.lazy:
            return self._read(seed)
        if seed not in self.models:
            state = self._read(seed)
            self.models[seed] = {k: v.pin_memory() for k, v in state.items()} if self.device == "cuda" else state
        return self.models[seed]

    def _ready(self, seed):
        """The model that holds juror `seed`'s weights, ready to score."""
        state = self._load(seed)
        if self.device != "cuda":
            return state
        self._gpu.load_state_dict(state)
        return self._gpu

    def tokenise(self, texts):
        return self.tokenizer(list(texts), truncation=True, max_length=self.max_len)["input_ids"]

    def logits_of(self, seed, ids, batch_size=64):
        """Logits of one juror for already-tokenised essays (array in the input order)."""
        torch = self.torch
        model = self._ready(seed)
        pad = self.tokenizer.pad_token_id
        out = np.empty(len(ids), dtype=np.float32)
        order = np.argsort([len(x) for x in ids], kind="stable")
        with torch.no_grad():
            for i in range(0, len(order), batch_size):
                chunk = order[i:i + batch_size]
                x = torch.full((len(chunk), max(len(ids[j]) for j in chunk)), pad, dtype=torch.long)
                for r, j in enumerate(chunk):
                    x[r, :len(ids[j])] = torch.tensor(ids[j])
                x = x.to(self.device)
                out[chunk] = model(input_ids=x, attention_mask=(x != pad).long()).logits.squeeze(1).float().cpu().numpy()
        return out

    def score_many(self, texts, seeds=SEEDS):
        """Logits of the chosen jurors for many essays: array (n_essays, len(seeds)). Each juror visits the GPU once for the whole set."""
        ids = self.tokenise(texts)
        return np.column_stack([self.logits_of(s, ids) for s in seeds])


def trial(jury, calib, text, edited=None):
    """The events of one trial, in order: one 'juror' event per juror (seed order), then one 'summary'.

    If `edited` is given (the essay after typos) every juror scores both versions: the event carries its mark on the edited essay and,
    under 'before', its mark on the original; the summary counts how many jurors changed zone and whether the official verdict did.
    """
    ids = jury.tokenise([text] if edited is None else [text, edited])
    seeds = SEEDS
    logit = {}
    for i, s in enumerate(seeds):
        lg = jury.logits_of(s, ids)
        logit[s] = lg
        shown = lg[-1]
        ev = {"type": "juror", "i": i, **calib.mark(s, shown)}
        if edited is not None:
            ev["before"] = calib.mark(s, lg[0])
        yield ev
    yield summary(calib, logit, with_before=edited is not None)


def summary(calib, logit, with_before=False):
    """Counts per zone and the official verdict, from {seed: logits}. The last logit is the essay shown, the first the original."""
    def tally(k):
        z = [str(zone_of(calib.p(s, [logit[s][k]])[0])) for s in SEEDS]
        counts = {name: z.count(name) for name in ZONES}
        official = calib.verdict([logit[s][k] for s in ENSEMBLE_SEEDS])
        return z, counts, official
    z, counts, official = tally(-1)
    out = {"type": "summary", "jurors": len(SEEDS), "counts": counts, "says_ai": counts["flagged"], "unsure": counts["above_usual"],
           "says_student": counts["not_flagged"], "official": official}
    if with_before:
        z0, counts0, official0 = tally(0)
        out["before"] = {"counts": counts0, "says_ai": counts0["flagged"], "unsure": counts0["above_usual"], "says_student": counts0["not_flagged"], "official": official0}
        out["jurors_changed_zone"] = int(sum(a != b for a, b in zip(z, z0)))
        out["jurors_changed_flag"] = int(sum((a == "flagged") != (b == "flagged") for a, b in zip(z, z0)))
        out["official_changed"] = official["zone"] != official0["zone"]
    return out
