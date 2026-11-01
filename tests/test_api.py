import io

import numpy as np
import pytest

from api import results, settings
from conftest import AI_ESSAY, SHORT, STUDENT_ESSAY

FRENCH = ("Ceci est un essai en français sur les voitures sans conducteur. Les voitures sont une partie de la vie des gens dans "
          "les villes et il faut que nous pensions à ce que cela veut dire pour tous les habitants de la ville et pour leurs enfants.")


def post(client, path, **body):
    return client.post(f"/api/{path}", json=body)


# ---------- /api/meta ----------
def test_meta_reads_thresholds_and_rates_from_the_results_files(client):
    m = client.get("/api/meta").json()
    assert m["thresholds"]["strict"] == pytest.approx(7.7965, abs=1e-3) and m["thresholds"]["standard"] == pytest.approx(4.666, abs=1e-3)
    assert m["rates"]["strict"]["unseen_topics_percent"] == 2.3 and m["rates"]["standard"]["unseen_topics_percent"] == 3.9
    assert m["rates"]["strict"]["worst_topic"] == {"topic": "Summer projects", "percent": 5.2}
    assert m["rates"]["standard"]["worst_topic"]["percent"] == 7.7
    assert m["trained_on"] == 28006
    assert m["limits"]["min_words"] == 40 and m["limits"]["max_tokens"] == 512
    assert m["attacks"]["caught_after"]["t5_heavy"] == 96.41 and m["attacks"]["humans_flagged"]["t5"] == 2.67
    assert m["attacks"]["caught_after"]["original"] == 99.58 and m["attacks"]["caught_after"]["typos5"] == 99.37
    assert m["attacks"]["words_changed_percent"] == {"typos5": 4.05, "typos10": 8.2, "t5": 15.33, "t5_heavy": 42.55}


def test_meta_examples_carry_their_known_labels(client):
    ex = client.get("/api/meta").json()["examples"]
    assert [e["label"] for e in ex] == ["ai", "human", "human"]
    assert [e["name"] for e in ex][2] == "Student essay it wrongly flags"
    assert all(e["words"] >= 40 and e["text"] for e in ex)


# ---------- /api/score ----------
def test_score_returns_logit_and_reading_info(client):
    r = post(client, "score", text=AI_ESSAY).json()
    assert r["logit"] == 9.0 and r["words"] == len(AI_ESSAY.split())
    assert r["truncated"] is False and r["read_chars"] == len(AI_ESSAY) and r["tokens_read"] == r["tokens"]


def test_long_essay_reports_where_reading_stopped(client):
    text = (AI_ESSAY + "\n\n") * 3                      # about 950 words of real prose
    r = post(client, "score", text=text).json()
    assert r["truncated"] is True and r["tokens_read"] == 512 and r["tokens"] > 512
    assert len(text[:r["read_chars"]].split()) == 512      # the fake tokenizer is one token per word


def test_too_short_says_how_many_more_words(client):
    r = post(client, "score", text=SHORT)
    assert r.status_code == 422 and r.json()["code"] == "too_short" and "36 more to go" in r.json()["detail"]


def test_not_english_is_refused_and_named(client):
    r = post(client, "score", text=FRENCH)
    assert r.status_code == 422 and r.json()["code"] == "not_english" and "French" in r.json()["detail"]


def test_too_long_is_refused(client):
    r = post(client, "score", text="word " * (settings.MAX_CHARS // 4))
    assert r.status_code == 413 and r.json()["code"] == "too_long"


def test_bad_body_gets_a_plain_sentence(client):
    r = client.post("/api/score", json={"nope": 1})
    assert r.status_code == 422 and r.json()["code"] == "bad_request" and "not understood" in r.json()["detail"]


# ---------- /api/explain ----------
def fake_explain(monkeypatch, values):
    from src.explain import sentence_spans

    def occlusion(det, text):
        spans = sentence_spans(text)
        return spans, np.array(values(len(spans)), dtype=float), None

    monkeypatch.setattr("src.explain.occlusion", occlusion)
    monkeypatch.setattr("src.explain.integrated_gradients", lambda det, text, steps=128: (None, np.linspace(0.1, 0.9, len(sentence_spans(text)))))


def test_explain_uses_occlusion_when_it_moves_the_score(client, monkeypatch):
    fake_explain(monkeypatch, lambda n: np.linspace(0, 3, n))
    r = post(client, "explain", text=AI_ESSAY).json()
    assert r["method"] == "occlusion" and r["list_truncated"] is False
    assert all(0 <= s["start"] < s["end"] <= len(AI_ESSAY) for s in r["sentences"])
    assert r["sentences"][-1]["score"] == pytest.approx(3.0)


def test_explain_falls_back_to_integrated_gradients_when_occlusion_is_flat(client, monkeypatch):
    fake_explain(monkeypatch, lambda n: np.full(n, 0.01))
    r = post(client, "explain", text=AI_ESSAY).json()
    assert r["method"] == "integrated_gradients"


def test_explain_marks_sentences_beyond_the_read_text_as_null(client, monkeypatch):
    fake_explain(monkeypatch, lambda n: [1.0] * (n - 1) + [float("nan")])
    assert post(client, "explain", text=AI_ESSAY).json()["sentences"][-1]["score"] is None


# ---------- /api/attribution ----------
def test_attribution_returns_top_three_with_the_warning_figure(client):
    r = post(client, "attribution", text=AI_ESSAY).json()
    assert [f["family"] for f in r["families"]] == ["Mistral", "Llama 2", "GPT-3.5"] and r["heldout_accuracy"] == "0–28%"


# ---------- /api/rewrite ----------
def test_typos_use_inject_typos_with_the_notebook_seed(client):
    from src.paraphraser import inject_typos
    r = post(client, "rewrite", text=STUDENT_ESSAY, method="typos5").json()
    assert r["edited"] == inject_typos(STUDENT_ESSAY, 0.05, seed=42) and r["edited"] != STUDENT_ESSAY
    assert 0 < r["words_changed"] and r["words_changed_share"] == pytest.approx(r["words_changed"] / len(STUDENT_ESSAY.split()), abs=0.01)
    assert "logit" in r and r["method"] == "typos5"


def test_same_seed_same_typos_other_seed_other_typos(client):
    a = post(client, "rewrite", text=STUDENT_ESSAY, method="typos10", seed=1).json()["edited"]
    assert a == post(client, "rewrite", text=STUDENT_ESSAY, method="typos10", seed=1).json()["edited"]
    assert a != post(client, "rewrite", text=STUDENT_ESSAY, method="typos10", seed=2).json()["edited"]


def test_t5_and_heavy_t5_run_the_paraphraser(client):
    for m in ("t5", "t5_heavy"):
        r = post(client, "rewrite", text=AI_ESSAY, method=m).json()
        assert "advantages" in r["edited"] and r["words_changed"] > 0


def test_t5_missing_is_a_clear_503(client, monkeypatch):
    monkeypatch.setattr(results, "t5_available", lambda: False)
    r = post(client, "rewrite", text=AI_ESSAY, method="t5")
    assert r.status_code == 503 and r.json()["code"] == "model_missing" and "Typos still work" in r.json()["detail"]
    assert post(client, "rewrite", text=AI_ESSAY, method="typos5").status_code == 200


def test_unknown_method_is_refused(client):
    r = post(client, "rewrite", text=AI_ESSAY, method="shuffle")
    assert r.status_code == 422 and "typos5" in r.json()["detail"]


# ---------- /api/batch ----------
def docx_bytes(text):
    from docx import Document
    d, buf = Document(), io.BytesIO()
    for para in text.split("\n\n"):
        d.add_paragraph(para)
    d.save(buf)
    return buf.getvalue()


def pdf_bytes(text):
    stream = f"BT /F1 11 Tf 40 750 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)


def blank_pdf():
    from pypdf import PdfWriter
    w, buf = PdfWriter(), io.BytesIO()
    w.add_blank_page(width=200, height=200)
    w.write(buf)
    return buf.getvalue()


def upload(client, files):
    return client.post("/api/batch", files=[("files", f) for f in files])


def test_batch_scores_txt_docx_and_pdf_in_order(client):
    one_line = " ".join(AI_ESSAY.split())
    r = upload(client, [("a.txt", AI_ESSAY.encode(), "text/plain"), ("b.docx", docx_bytes(STUDENT_ESSAY), "application/octet-stream"),
                        ("c.pdf", pdf_bytes(one_line), "application/pdf")]).json()["results"]
    assert [x["name"] for x in r] == ["a.txt", "b.docx", "c.pdf"] and all(x["error"] is None for x in r)
    assert [x["logit"] for x in r] == [9.0, -6.0, 9.0] and r[0]["words"] == len(AI_ESSAY.split())
    assert "driverless" in r[1]["text"] or "phone" in r[1]["text"]          # extracted text comes back for scored files


def test_batch_reports_each_bad_file_without_failing_the_others(client):
    r = upload(client, [("good.txt", AI_ESSAY.encode(), "text/plain"), ("scan_0007.jpg", b"\xff\xd8", "image/jpeg"),
                        ("blank.pdf", blank_pdf(), "application/pdf"), ("kofi.txt", SHORT.encode(), "text/plain"),
                        ("french.txt", FRENCH.encode(), "text/plain"), ("broken.docx", b"not a zip", "application/octet-stream")]).json()["results"]
    assert r[0]["error"] is None and r[0]["logit"] == 9.0
    assert [x["error"]["code"] for x in r[1:]] == ["unsupported_file", "no_text", "too_short", "not_english", "unreadable"]
    assert r[3]["words"] == 4 and r[3]["logit"] is None and r[3]["text"] is None


def test_batch_too_many_files(client):
    files = [(f"{i}.txt", AI_ESSAY.encode(), "text/plain") for i in range(settings.MAX_FILES_PER_REQUEST + 1)]
    r = upload(client, files)
    assert r.status_code == 413 and r.json()["code"] == "too_many_files"


# ---------- rate limit ----------
def test_rate_limit_answers_429_with_cors_headers(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MIN", 3)
    for _ in range(3):
        assert client.post("/api/score", json={"text": AI_ESSAY}).status_code == 200
    r = client.post("/api/score", json={"text": AI_ESSAY}, headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and int(r.headers["retry-after"]) >= 1
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"      # the old middleware lost this header


def test_a_batch_costs_one_unit_per_ten_files(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MIN", 3)
    files = [(f"{i}.txt", AI_ESSAY.encode(), "text/plain") for i in range(25)]     # 25 files = 3 units
    assert upload(client, files).status_code == 200
    assert client.post("/api/score", json={"text": AI_ESSAY}).status_code == 429


# ---------- the web page ----------
def test_deep_links_get_index_html_and_api_paths_stay_json(client, monkeypatch, tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "x.js").write_text("console.log(1)")
    monkeypatch.setattr(settings, "DIST", tmp_path)
    assert client.get("/fool").text == "<html>app</html>"
    assert client.get("/assets/x.js").text == "console.log(1)"
    assert client.get("/../../etc/passwd").text == "<html>app</html>"               # no escape from dist
    assert client.get("/api/nope").json()["code"] == "not_found"
