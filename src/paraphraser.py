"""Paraphrasers used by 13_attack.ipynb and the demo.

- `Seq2SeqParaphraser`: the GRU + Bahdanau-attention model built and trained in 12_paraphraser.ipynb
  (same architecture, loaded from models/paraphraser_gru.pt).
- `T5Paraphraser`: pretrained `Vamsi/T5_Paraphrase_Paws` (T5-base fine-tuned on PAWS).

Both paraphrase essays one sentence at a time and keep the essay's paragraph breaks.
"""
import json
import re
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

MODELS = Path(__file__).resolve().parent.parent / "models"
PAD, BOS, EOS, UNK = range(4)
N_SPECIAL = 4


class Seq2Seq(nn.Module):
    """Same network as in 12_paraphraser.ipynb (see the explanation there)."""

    def __init__(self, vocab, emb=256, hid=256, dropout=0.2):
        super().__init__()
        self.emb = nn.Embedding(vocab, emb, padding_idx=PAD)
        self.encoder = nn.GRU(emb, hid, batch_first=True, bidirectional=True)
        self.init_state = nn.Linear(2 * hid, 2 * hid)
        self.W_h = nn.Linear(2 * hid, 2 * hid, bias=False)
        self.W_s = nn.Linear(2 * hid, 2 * hid)
        self.v = nn.Linear(2 * hid, 1, bias=False)
        self.decoder = nn.GRUCell(emb + 2 * hid, 2 * hid)
        self.out = nn.Linear(2 * hid + 2 * hid + emb, vocab)
        self.drop = nn.Dropout(dropout)

    def encode(self, src):
        H, h_last = self.encoder(self.drop(self.emb(src)))
        s0 = torch.tanh(self.init_state(torch.cat([h_last[0], h_last[1]], dim=-1)))
        return H, self.W_h(H), s0

    def attend(self, H, H_proj, s, src_mask):
        scores = self.v(torch.tanh(H_proj + self.W_s(s).unsqueeze(1))).squeeze(-1)
        alpha = F.softmax(scores.masked_fill(~src_mask, -1e4), dim=-1)
        return torch.bmm(alpha.unsqueeze(1), H).squeeze(1), alpha

    def step(self, prev_tok, s, H, H_proj, src_mask):
        e = self.drop(self.emb(prev_tok))
        ctx, alpha = self.attend(H, H_proj, s, src_mask)
        s = self.decoder(torch.cat([e, ctx], -1), s)
        return self.out(torch.cat([s, ctx, e], -1)), s, alpha


def split_sentences(text):
    """Split into sentences, keeping the exact whitespace between them so paragraphs survive."""
    parts = re.split(r"(?<=[.!?])(\s+)", text)
    return parts[0::2], parts[1::2]          # sentences, separators


def join_sentences(sentences, separators):
    out = []
    for i, s in enumerate(sentences):
        out.append(s)
        if i < len(separators):
            out.append(separators[i])
    return "".join(out)


def clean_spacing(s):
    """Undo tokenizer spacing artefacts like 'monkey .' or "someone 's" so they can't act as a signal."""
    s = re.sub(r"\s+([.,;:!?%)])", r"\1", s)
    s = re.sub(r"\s+('s|'re|'ve|'ll|'d|'m|n't)\b", r"\1", s)
    s = re.sub(r"([(])\s+", r"\1", s)
    return re.sub(r"\s{2,}", " ", s).strip()


class _SentenceParaphraser:
    def paraphrase_sentences(self, sentences, **kw):
        raise NotImplementedError

    def paraphrase_essays(self, essays, batch_size=64, **kw):
        """Paraphrase every sentence of every essay; returns the rewritten essays."""
        splits = [split_sentences(t) for t in essays]
        flat = [s for sents, _ in splits for s in sents]
        todo = [i for i, s in enumerate(flat) if s.strip()]
        new = list(flat)
        for b in range(0, len(todo), batch_size):
            idx = todo[b:b + batch_size]
            for i, p in zip(idx, self.paraphrase_sentences([flat[i] for i in idx], **kw)):
                new[i] = clean_spacing(p) if p.strip() else flat[i]
        out, k = [], 0
        for sents, seps in splits:
            out.append(join_sentences(new[k:k + len(sents)], seps))
            k += len(sents)
        return out


class Seq2SeqParaphraser(_SentenceParaphraser):
    def __init__(self, device="cuda"):
        from transformers import AutoTokenizer
        cfg = json.load(open(MODELS / "paraphraser_vocab.json"))
        self.tok = AutoTokenizer.from_pretrained("gpt2")
        self.max_tok = cfg["max_tok"]
        self.to_ours = {t: i + N_SPECIAL for i, t in enumerate(cfg["kept_gpt2_ids"])}
        self.to_gpt2 = {i: t for t, i in self.to_ours.items()}
        self.device = device
        self.model = Seq2Seq(N_SPECIAL + len(cfg["kept_gpt2_ids"]), cfg["emb"], cfg["hid"]).to(device)
        self.model.load_state_dict(torch.load(MODELS / "paraphraser_gru.pt", map_location=device))
        self.model.eval()

    @torch.no_grad()
    def _generate(self, src_lists, sample, temperature, top_k, rng_seed):
        m, dev = self.model, self.device
        gen = torch.Generator(device=dev).manual_seed(rng_seed)
        B, S = len(src_lists), max(len(x) for x in src_lists)
        src = torch.full((B, S), PAD, dtype=torch.long)
        for r, x in enumerate(src_lists):
            src[r, :len(x)] = torch.tensor(x)
        src = src.to(dev)
        mask = src != PAD
        H, H_proj, s = m.encode(src)
        prev = torch.full((B,), BOS, dtype=torch.long, device=dev)
        out = [[] for _ in range(B)]
        done = torch.zeros(B, dtype=torch.bool, device=dev)
        for _ in range(int(S * 1.5) + 5):
            logits, s, _ = m.step(prev, s, H, H_proj, mask)
            logits = logits.float()
            logits[:, [PAD, BOS, UNK]] = -1e9
            for r in range(B):                       # trigram blocking, as in 12
                seq = out[r]
                for i in range(len(seq) - 2):
                    if seq[i] == seq[-2] and seq[i + 1] == seq[-1]:
                        logits[r, seq[i + 2]] = -1e9
            if sample:
                top = logits.topk(top_k, -1)
                pick = torch.multinomial(F.softmax(top.values / temperature, -1), 1, generator=gen)
                nxt = top.indices.gather(1, pick).squeeze(1)
            else:
                nxt = logits.argmax(-1)
            for r in range(B):
                if not done[r] and nxt[r].item() != EOS:
                    out[r].append(nxt[r].item())
            done |= nxt == EOS
            if done.all():
                break
            prev = torch.where(done, torch.full_like(nxt, EOS), nxt)
        return out

    def paraphrase_sentences(self, sentences, sample=True, temperature=0.8, top_k=10, seed=0):
        ids = self.tok(sentences)["input_ids"]
        res = list(sentences)
        ok = [i for i, x in enumerate(ids) if 0 < len(x) <= self.max_tok]   # longer sentences stay unchanged
        if ok:
            src = [[self.to_ours.get(t, UNK) for t in ids[i]] for i in ok]
            outs = self._generate(src, sample, temperature, top_k, seed)
            for i, o in zip(ok, outs):
                res[i] = self.tok.decode([self.to_gpt2[t] for t in o if t >= N_SPECIAL]).strip()
        return res


class T5Paraphraser(_SentenceParaphraser):
    NAME = "Vamsi/T5_Paraphrase_Paws"

    def __init__(self, device="cuda"):
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        self.tok = AutoTokenizer.from_pretrained(self.NAME)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.NAME, dtype=torch.float16).to(device).eval()
        self.device = device

    @torch.no_grad()
    def paraphrase_sentences(self, sentences, temperature=1.0, top_p=0.9, top_k=50, seed=0):
        torch.manual_seed(seed)
        enc = self.tok([f"paraphrase: {s} </s>" for s in sentences], return_tensors="pt", padding=True,
                       truncation=True, max_length=128).to(self.device)
        out = self.model.generate(**enc, do_sample=True, temperature=temperature, top_p=top_p, top_k=top_k,
                                  max_new_tokens=int(enc["input_ids"].shape[1] * 1.5) + 8)
        return self.tok.batch_decode(out, skip_special_tokens=True)


def words_changed(original, edited):
    """Share of the original's words that were inserted, deleted or replaced (word-level diff, as in 13_attack)."""
    import difflib
    wa, wb = original.split(), edited.split()
    ops = difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes()
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in ops if op != "equal") / max(len(wa), 1)


def inject_typos(text, rate, seed=0):
    """Corrupt a share `rate` of words (letters only, length >= 3) with one random character edit:
    swap two adjacent letters, delete a letter, or double a letter."""
    rng = np.random.default_rng(seed)
    def corrupt(m):
        w = m.group(0)
        if len(w) < 3 or rng.random() >= rate:
            return w
        i = int(rng.integers(0, len(w) - 1))
        op = rng.integers(0, 3)
        if op == 0:
            return w[:i] + w[i + 1] + w[i] + w[i + 2:]
        if op == 1:
            return w[:i] + w[i + 1:]
        return w[:i] + w[i] + w[i:]
    return re.sub(r"[A-Za-z]+", corrupt, text)
