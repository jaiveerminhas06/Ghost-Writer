"""Upload the two model files the hosted demo needs to a Hugging Face model repo (one-off).

    huggingface-cli login            # paste a write token once
    python deploy/upload_models.py <your-username>/ghost-writer-models
Then set GW_MODEL_REPO to that name in the Space's settings.
"""
import sys
from pathlib import Path

from huggingface_hub import HfApi

repo = sys.argv[1]
models = Path(__file__).resolve().parent.parent / "models"
api = HfApi()
api.create_repo(repo, repo_type="model", exist_ok=True)
api.upload_folder(repo_id=repo, folder_path=models / "distilroberta_finetuned", path_in_repo="distilroberta_finetuned")
api.upload_file(repo_id=repo, path_or_fileobj=models / "attribution_tfidf_logreg.joblib", path_in_repo="attribution_tfidf_logreg.joblib")
print("uploaded to", repo)
