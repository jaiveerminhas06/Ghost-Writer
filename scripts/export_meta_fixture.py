"""Write the part of /api/meta the front-end unit tests need to frontend/src/lib/meta.fixture.json.

    python scripts/export_meta_fixture.py

The front end's tests (npm test) run in Node and cannot call the API, so they read this file. tests/test_jury_api.py checks that the file
still equals what the API returns, so a figure that changes in results/ cannot leave the front-end tests quietly out of date.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from api import results

OUT = ROOT / "frontend" / "src" / "lib" / "meta.fixture.json"


def trimmed():
    m = results.meta(jury_live=True)
    j = m["jury"]
    return {"api_version": m["api_version"], "official": m["official"],
            "jury": {"api": j["api"], "live": j["live"], "scale": j["scale"], "attacks_final": j["attacks_final"],
                     "statistics": {"S3": {"heldout_prompt_humans": j["statistics"]["S3"]["heldout_prompt_humans"]}}},
            "examples": [{k: e[k] for k in ("id", "name", "label", "kind", "note", "words")} for e in m["examples"]]}


if __name__ == "__main__":
    OUT.write_text(json.dumps(trimmed(), indent=1, sort_keys=True) + "\n")
    print("wrote", OUT)
