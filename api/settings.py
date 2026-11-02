"""Every tunable number of the web API, in one place. Environment variables override the defaults."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Bump this when /api/meta or any response changes shape. The page knows which version it was built for and says so when they differ.
API_VERSION = 3          # 3: /api/meta lists demo_classes (two topics) instead of one demo_class

# --- the detector's rules -------------------------------------------------------------------------
MIN_WORDS = 40                 # below this a score would mean little (same rule as demo/app.py)
MAX_CHARS = 30_000             # longest essay accepted
MAX_SENTENCES = 80             # highlights are computed for at most this many sentences
SATURATED = 0.5                # occlusion changes below this on every sentence = flat (notebook 14): use integrated gradients
IG_STEPS = int(os.environ.get("GW_IG_STEPS", "128"))     # 128 locally; the CPU host sets 32 (ranking checked on 3 essays)
FLAG_RATES = {"strict": 0.005, "standard": 0.01}         # target false-positive rates chosen in notebook 09

# --- attacks ---------------------------------------------------------------------------------------
ATTACK_SEED = 42               # notebook 13's SEED; one essay on the page is notebook index 0, so seed 42 for typos and T5
ATTACKS = {                    # method -> (kind, setting)
    "typos5": ("typos", 0.05),
    "typos10": ("typos", 0.10),
    "t5": ("t5", 1.0),         # notebook 13: "T5 paraphrase (T=1.0)"
    "t5_heavy": ("t5", 1.5),   # notebook 13: "T5 paraphrase (T=1.5)"
}

# --- limits against overload (a public demo needs them; the owner's laptop never notices) -------------
RATE_LIMIT_PER_MIN = float(os.environ.get("GW_RATE_LIMIT", "60"))   # cost units per visitor per minute
BATCH_FILES_PER_UNIT = 10      # a batch of files costs one unit per ten files (at least one)
MAX_FILES_PER_REQUEST = 50
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_REQUEST_BYTES = 20 * 1024 * 1024   # a whole upload; anything larger is refused before it is read, so no upload can reach the disk
MAX_PDF_PAGES = 60
LOCK_WAIT_SECONDS = 120        # how long a request waits for the model before answering "busy"

# --- the language check --------------------------------------------------------------------------
MIN_LATIN_SHARE = 0.60         # share of letters that must be Latin-script
MIN_ENGLISH_SHARE = 0.10       # share of words that must be common English function words, whatever else wins
CLEAR_ENGLISH_SHARE = 0.20     # at or above this the essay is accepted even if another language scores higher

# --- results files the page quotes (every number shown comes from one of these) ---------------------
RESULTS = ROOT / "results"
SAMPLES_JSON = ROOT / "demo" / "samples.json"
SPLITS_CSV = ROOT / "data" / "processed" / "splits.csv"
DEMO_CLASS = ROOT / "demo" / "class_sample"      # the demo class: essays, labels.json and how they were picked

# --- hosting -------------------------------------------------------------------------------------
EXTRA_ORIGINS = [o for o in os.environ.get("GW_ORIGINS", "").split(",") if o]
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
DIST = ROOT / "frontend" / "dist"
