"""Shared test setup: a fake detector so the API tests run in seconds without a GPU or the model files."""
import re

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api import limiter, main, results, settings

SAMPLES = {e["label"] + str(e["id"]): e["text"] for e in results.examples()}
AI_ESSAY = results.examples()[0]["text"]
STUDENT_ESSAY = results.examples()[1]["text"]
SHORT = "Too short to score."


class FakeTokenizer:
    """One token per word; the same call signature as the Hugging Face tokenizer's offsets."""
    def __call__(self, text, truncation=False, max_length=None, return_offsets_mapping=False):
        spans = [m.span() for m in re.finditer(r"\S+", text)]
        if truncation and max_length:
            spans = spans[:max_length]
        out = {"input_ids": list(range(len(spans)))}
        if return_offsets_mapping:
            out["offset_mapping"] = spans
        return out


class FakeDetector:
    max_len = 512
    tok = FakeTokenizer()

    def score(self, texts):
        # "AI-like" if the text uses the Claude example's favourite words; otherwise student-like
        return np.array([9.0 if "advantages" in t.lower() else -6.0 for t in texts], dtype=np.float32)


class FakeT5:
    def paraphrase_essays(self, texts, temperature=1.0, seed=0):
        return [t.replace("benefits", "advantages") for t in texts]


class FakeJury:
    """Stands in for src/jury.Jury: no models. A text that uses the Claude example's favourite words is 'AI' (a logit above every
    juror's flag line); anything else is student-like. `degrade_unless` makes every other AI-like text score low, as heavy typos can."""
    tokenizer = FakeTokenizer()

    def __init__(self, live=True):
        self.live, self.degrade_unless, self.calls = live, None, 0

    def logit(self, seed, text):
        if "advantages" in text.lower():
            return 0.0 if (self.degrade_unless is not None and text != self.degrade_unless) else 9.8
        return -6.0 + 0.01 * (seed - 42)

    def tokenise(self, texts):
        return list(texts)                      # the 'ids' are the texts themselves, opaque to src/jury.trial

    def logits_of(self, seed, ids):
        self.calls += 1
        return np.array([self.logit(seed, t) for t in ids], dtype=np.float32)

    def score_many(self, texts, seeds=None):
        from src.jury import SEEDS
        return np.column_stack([self.logits_of(s, list(texts)) for s in (SEEDS if seeds is None else seeds)])


@pytest.fixture
def jury(monkeypatch):
    fake = FakeJury()
    monkeypatch.setattr(main, "jury", lambda: fake)
    return fake


@pytest.fixture
def client(monkeypatch, jury):
    monkeypatch.setattr(main, "detector", lambda: FakeDetector())
    monkeypatch.setattr(main, "attribution_model", lambda: object())
    monkeypatch.setattr(main, "t5", lambda: FakeT5())
    monkeypatch.setattr(results, "t5_available", lambda: True)
    monkeypatch.setattr("src.attribution.most_similar", lambda model, text, k=3: [("Mistral", 0.37), ("Llama 2", 0.18), ("GPT-3.5", 0.13)][:k])
    limiter.reset()
    return TestClient(main.app)
