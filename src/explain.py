"""Explanations for the DistilRoBERTa detector (14_explain.ipynb and the demo).

Two methods, both returning one score per sentence (positive = pushes the essay towards "AI"):
- `occlusion`: remove each sentence in turn and measure how much the detector's logit falls.
- `integrated_gradients`: attribute the logit to every token (Sundararajan et al., 2017), then sum the
  token attributions inside each sentence.

Only the first 512 tokens are seen by the detector, so sentences that start after that point get NaN.
"""
import re

import numpy as np
import torch


def sentence_spans(text):
    """Character spans (start, end) of each sentence. A sentence ends at . ! or ? followed by whitespace."""
    spans, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+", text):
        spans.append((start, m.start()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def visible_chars(det, text):
    """Index of the last character the detector actually reads (it truncates at max_len tokens)."""
    offsets = det.tok(text, truncation=True, max_length=det.max_len, return_offsets_mapping=True)["offset_mapping"]
    return max(e for s, e in offsets)


def occlusion(det, text):
    """Per sentence: logit(full essay) - logit(essay without that sentence)."""
    spans = sentence_spans(text)
    limit = visible_chars(det, text)
    variants, idx = [], []
    for i, (s, e) in enumerate(spans):
        if s >= limit:
            continue
        cut_end = spans[i + 1][0] if i + 1 < len(spans) else len(text)   # remove the sentence and the space after it
        variants.append(text[:s] + text[cut_end:])
        idx.append(i)
    scores = det.score([text] + variants)
    out = np.full(len(spans), np.nan)
    out[idx] = scores[0] - scores[1:]
    return spans, out, float(scores[0])


def integrated_gradients(det, text, steps=128, chunk=16):
    """Token attributions by integrated gradients, summed per sentence.

    Baseline: the same essay with every real token replaced by <pad> (start/end tokens kept).
    Path: straight line in embedding space from baseline to the essay, `steps` midpoint samples.
    Returns sentence spans, per-sentence attribution, per-token attribution, token offsets, and the
    completeness check: attributions should sum to logit(essay) - logit(baseline).
    """
    model, tok, dev = det.model, det.tok, det.device
    enc = tok(text, truncation=True, max_length=det.max_len, return_offsets_mapping=True, return_tensors="pt")
    ids = enc["input_ids"].to(dev)
    offsets = enc["offset_mapping"][0].tolist()
    emb = model.roberta.embeddings.word_embeddings
    special = (ids == tok.bos_token_id) | (ids == tok.eos_token_id)
    base_ids = torch.where(special, ids, torch.full_like(ids, tok.pad_token_id))
    mask = torch.ones_like(ids)
    for p in model.parameters():
        p.requires_grad_(False)
    with torch.no_grad():
        x, b = emb(ids).float(), emb(base_ids).float()
    alphas = (torch.arange(steps, device=dev, dtype=torch.float32) + 0.5) / steps
    grad_sum = torch.zeros_like(x)
    for a in alphas.split(chunk):
        inp = (b + a.view(-1, 1, 1) * (x - b)).requires_grad_(True)
        with torch.autocast("cuda", dtype=torch.float16):
            logit = model(inputs_embeds=inp, attention_mask=mask.expand(len(a), -1)).logits.squeeze(-1)
        grad_sum += torch.autograd.grad(logit.float().sum(), inp)[0].sum(0, keepdim=True)
    token_attr = ((x - b) * grad_sum / steps).sum(-1).squeeze(0).detach().cpu().numpy()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        f_x = model(inputs_embeds=x, attention_mask=mask).logits.float().item()
        f_b = model(inputs_embeds=b, attention_mask=mask).logits.float().item()

    spans = sentence_spans(text)
    limit = max(e for s, e in offsets)
    sent_attr = np.full(len(spans), np.nan)
    for i, (s, e) in enumerate(spans):
        if s < limit:
            sent_attr[i] = sum(t for t, (ts, te) in zip(token_attr, offsets) if te > ts and s <= ts < e)
    completeness = {"sum_of_attributions": float(token_attr.sum()), "logit_essay": f_x, "logit_baseline": f_b,
                    "gap": float(token_attr.sum() - (f_x - f_b))}
    return spans, sent_attr, token_attr, offsets, completeness
