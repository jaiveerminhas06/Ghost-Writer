"""The promises on the Check a class page: "Scores are kept on this computer and cleared when you close the tab", plus the
footer's "not stored or logged". The server must read an upload in memory, write nothing to disk, and never log essay text."""
import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import settings, uploads
from conftest import AI_ESSAY, STUDENT_ESSAY

MARKER = "zebracornquartz"          # a word that appears in no log, error message or example, so finding it means the text leaked
ESSAY = STUDENT_ESSAY.replace("Dear Principal", f"Dear Principal {MARKER}", 1)
ROOT = Path(__file__).resolve().parent.parent


def tree(root):
    """Every file under root, ignoring caches that tools create on their own."""
    skip = {"__pycache__", ".pytest_cache", "node_modules", ".git", "dist", ".ipynb_checkpoints"}
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and not (skip & set(p.relative_to(root).parts))}


@pytest.fixture
def no_disk(tmp_path, monkeypatch):
    """Point the temp folder at an empty directory and record every time a spooled upload rolls over to a file on disk.
    The roll-over is still allowed to happen, so a test can see that it did. The record is the evidence: Python's temporary files
    are anonymous (unlinked as soon as they are created), so a listing of the folder shows nothing even when data was written."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    rollovers = []
    original = tempfile.SpooledTemporaryFile.rollover

    def spy(self):
        rollovers.append(1)
        return original(self)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", spy)
    return SimpleNamespace(path=tmp_path, rollovers=rollovers)


def upload(client, files):
    return client.post("/api/batch", files=[("files", f) for f in files])


def test_a_large_upload_stays_in_memory(client, no_disk):
    # 3 MB is over Starlette's default 1 MB spool size: without api/uploads.py this file would be written to the temp folder
    big = ("word " * 600_000).encode()
    assert len(big) > 1024 * 1024 * 2.5
    r = upload(client, [("big.txt", big, "text/plain"), ("essay.txt", ESSAY.encode(), "text/plain")])
    assert r.status_code == 200
    results = r.json()["results"]
    assert results[0]["error"]["code"] in {"too_long", "not_english"}        # refused as an essay, but read without touching the disk
    assert results[1]["error"] is None
    assert no_disk.rollovers == []                                            # no upload was ever moved from memory to a file
    assert list(no_disk.path.iterdir()) == []                                      # and the temp folder is still empty


def test_the_framework_default_would_have_written_that_file_to_disk(client, no_disk, monkeypatch):
    """The test above only means something if the default really does roll over. Put the default back and it must."""
    from starlette.formparsers import MultiPartParser
    monkeypatch.setattr(MultiPartParser, "spool_max_size", 1024 * 1024)
    upload(client, [("big.txt", ("word " * 600_000).encode(), "text/plain")])
    assert no_disk.rollovers != []        # the upload was moved from memory to a file (an anonymous one, so the folder listing stays empty)


def test_a_request_over_the_limit_is_refused_before_it_is_read(client, no_disk, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 200_000)
    r = upload(client, [("big.txt", b"x" * 400_000, "text/plain")])
    assert r.status_code == 413 and r.json()["code"] == "too_large"
    assert list(no_disk.path.iterdir()) == []


def test_a_request_with_no_declared_length_is_cut_off_while_streaming(client, no_disk, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 200_000)

    def chunks():                                 # an iterator body is sent without a Content-Length header
        for _ in range(10):
            yield b"y" * 60_000
    r = client.post("/api/score", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and r.json()["code"] == "too_large"


def test_nothing_is_written_anywhere_in_the_project_or_temp_folder(client, no_disk):
    before = tree(ROOT)
    upload(client, [("a.txt", ESSAY.encode(), "text/plain"), ("b.txt", AI_ESSAY.encode(), "text/plain")])
    client.post("/api/score", json={"text": ESSAY})
    assert tree(ROOT) == before
    assert list(no_disk.path.iterdir()) == []


def test_essay_text_never_reaches_the_logs(client, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    client.post("/api/score", json={"text": ESSAY})
    upload(client, [("a.txt", ESSAY.encode(), "text/plain"), ("short.txt", (MARKER + " too short").encode(), "text/plain")])
    client.post("/api/rewrite", json={"text": ESSAY, "method": "typos5"})
    client.post("/api/score", json={"text": MARKER})                          # the refusal for a short text must not echo it back into a log
    out = capsys.readouterr()
    assert MARKER not in caplog.text and MARKER not in out.out and MARKER not in out.err
    assert not any(MARKER in str(a) for rec in caplog.records for a in (rec.args if isinstance(rec.args, tuple) else (rec.args,)))
