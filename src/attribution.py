"""Generator-attribution model for the demo: TF-IDF + multinomial logistic regression.

11_attribution.ipynb showed that attribution looks excellent on a random split (macro-F1 0.976 with TF-IDF)
but collapses to chance on a data source it has never seen (0-28% right). The demo therefore shows it only
as "most similar training sources", with that warning (decision of 2026-10-25). Logistic regression is used
instead of the LinearSVC of 11 because the demo needs probabilities.
"""
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "models" / "attribution_tfidf_logreg.joblib"

FAMILY = {
    'chat_gpt_moth': 'GPT-3.5', 'radek_500': 'GPT-3.5',
    'radekgpt4': 'GPT-4',
    'darragh_claude_v6': 'Claude', 'darragh_claude_v7': 'Claude',
    'kingki19_palm': 'PaLM', 'palm-text-bison1': 'PaLM',
    'cohere-command': 'Cohere',
    'llama2_chat': 'Llama 2', 'NousResearch/Llama-2-7b-chat-hf': 'Llama 2', 'llama_70b_v1': 'Llama 2',
    'mistral7binstruct_v1': 'Mistral', 'mistral7binstruct_v2': 'Mistral', 'mistralai/Mistral-7B-Instruct-v0.1': 'Mistral',
    'falcon_180b_v1': 'Falcon',
}
HELDOUT_SOURCE_ACCURACY = "0–28%"   # from 11_attribution, leave-one-source-out


def train_and_save():
    """Fit on every AI essay with a known family (17,490 essays) and save to models/."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from src.data import load_splits

    df = load_splits()
    ai = df[(df['label'] == 1) & df['source'].isin(FAMILY)]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=200_000, sublinear_tf=True),
        LogisticRegression(C=10, max_iter=2000, class_weight='balanced'),
    )
    model.fit(ai['text'], ai['source'].map(FAMILY))
    PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, PATH)
    return model


def load():
    from src.detector import model_path
    model_path(PATH.name)         # fetches it from the Hub repo if GW_MODEL_REPO is set and the file is missing
    return joblib.load(PATH) if PATH.exists() else train_and_save()


def most_similar(model, text, k=3):
    """Top-k families by predicted probability, as [(family, probability), ...]."""
    proba = model.predict_proba([text])[0]
    order = proba.argsort()[::-1][:k]
    return [(model.classes_[i], float(proba[i])) for i in order]
