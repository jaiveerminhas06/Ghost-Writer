"""The fine-tuned DistilRoBERTa detector from 08_bert.ipynb, with the thresholds chosen in 09_threshold.ipynb.

Scores are logits (higher = more likely AI). Use the thresholds, not 0.5 / logit 0:
    det = Detector(); logits = det.score(texts); flagged = logits >= det.thresholds[0.01]
"""
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent


def default_device():
    """GPU when there is one (development laptop), CPU otherwise (hosted demo)."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def model_path(name):
    """models/<name>, downloading it first from the Hub repo named in GW_MODEL_REPO if it is not on disk.

    The weights are too large for git, so the hosted demo keeps them in a separate Hugging Face model repo.
    """
    import os
    path = ROOT / "models" / name
    repo = os.environ.get("GW_MODEL_REPO")
    if not path.exists() and repo:
        from huggingface_hub import snapshot_download
        snapshot_download(repo, allow_patterns=[f"{name}/*", name], local_dir=ROOT / "models")
    return path


class Detector:
    def __init__(self, device=None, max_len=512):
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        device = device or default_device()
        path = model_path("distilroberta_finetuned")
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForSequenceClassification.from_pretrained(path).to(device).eval()
        self.device, self.max_len = device, max_len
        t = pd.read_csv(ROOT / "results" / "09_thresholds.csv", index_col=0)["roberta"]
        # keys: target false-positive rate on val humans (0.05 / 0.01 / 0.005), plus 'default' (= logit 0)
        self.thresholds = {(k if k == "default" else float(k)): float(v) for k, v in t.items()}

    @torch.no_grad()
    def score(self, texts, batch_size=64):
        ids = self.tok(list(texts), truncation=True, max_length=self.max_len)["input_ids"]
        out = np.empty(len(ids), dtype=np.float32)
        order = np.argsort([len(x) for x in ids], kind="stable")
        pad = self.tok.pad_token_id
        for s in range(0, len(order), batch_size):
            chunk = order[s:s + batch_size]
            x = torch.full((len(chunk), max(len(ids[i]) for i in chunk)), pad, dtype=torch.long)
            for r, i in enumerate(chunk):
                x[r, :len(ids[i])] = torch.tensor(ids[i])
            with torch.autocast("cuda", dtype=torch.float16, enabled=self.device == "cuda"):
                logits = self.model(input_ids=x.to(self.device), attention_mask=(x != pad).long().to(self.device)).logits
            out[chunk] = logits.squeeze(1).float().cpu().numpy()
        return out


# ---------------------------------------------------------------------------------------------------------------
# Windowed scoring (added for 16_long_essays.ipynb). Detector.score above is unchanged.
# ---------------------------------------------------------------------------------------------------------------

def _score_windows(self, texts, stride=256, batch_size=64):
    """Score an essay in overlapping windows instead of only its first 512 tokens.

    The model sees at most 512 tokens (510 of text plus the start and end markers). An essay longer than that is cut by
    Detector.score. Here the essay is tokenised once, without cutting, and read in windows of 510 text tokens whose starts
    are `stride` tokens apart; the last window ends at the end of the essay. An essay of at most 510 tokens gets one window
    that is identical to Detector.score's input, so its score is the same.

    Returns two lists, one entry per essay: the logit of each window, and each window's length in tokens.
    """
    body = self.max_len - 2
    all_ids = self.tok(list(texts), add_special_tokens=False)["input_ids"]
    wins, owner = [], []
    for e, ids in enumerate(all_ids):
        starts = [0]
        while starts[-1] + body < len(ids):
            starts.append(starts[-1] + stride)
        for s in starts:
            wins.append([self.tok.cls_token_id] + ids[s:s + body] + [self.tok.sep_token_id])
            owner.append(e)
    logits = np.empty(len(wins), dtype=np.float32)
    order = np.argsort([len(w) for w in wins], kind="stable")
    pad = self.tok.pad_token_id
    with torch.no_grad():
        for s in range(0, len(order), batch_size):
            chunk = order[s:s + batch_size]
            x = torch.full((len(chunk), max(len(wins[i]) for i in chunk)), pad, dtype=torch.long)
            for r, i in enumerate(chunk):
                x[r, :len(wins[i])] = torch.tensor(wins[i])
            with torch.autocast("cuda", dtype=torch.float16, enabled=self.device == "cuda"):
                out = self.model(input_ids=x.to(self.device), attention_mask=(x != pad).long().to(self.device)).logits
            logits[chunk] = out.squeeze(1).float().cpu().numpy()
            del out
    owner = np.array(owner)
    lengths = np.array([len(w) for w in wins])
    cut = np.r_[0, np.flatnonzero(np.diff(owner)) + 1, len(owner)]
    return [logits[a:b] for a, b in zip(cut[:-1], cut[1:])], [lengths[a:b] for a, b in zip(cut[:-1], cut[1:])]


Detector.score_windows = _score_windows
