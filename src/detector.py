"""The fine-tuned DistilRoBERTa detector from 08_bert.ipynb, with the thresholds chosen in 09_threshold.ipynb.

Scores are logits (higher = more likely AI). Use the thresholds, not 0.5 / logit 0:
    det = Detector(); logits = det.score(texts); flagged = logits >= det.thresholds[0.01]
"""
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent


class Detector:
    def __init__(self, device="cuda", max_len=512):
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        path = ROOT / "models" / "distilroberta_finetuned"
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
            with torch.autocast("cuda", dtype=torch.float16):
                logits = self.model(input_ids=x.to(self.device), attention_mask=(x != pad).long().to(self.device)).logits
            out[chunk] = logits.squeeze(1).float().cpu().numpy()
        return out
