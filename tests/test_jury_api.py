"""POST /api/jury, the official verdict on /api/score and /api/batch, and the jury block of /api/meta. No GPU: the jurors are fakes
(conftest.FakeJury); the calibration and the results files are the real ones."""
import json

import pandas as pd
import pytest

from api import jury_api, main, results, settings
from conftest import AI_ESSAY, SHORT, STUDENT_ESSAY, FakeJury
from test_api import FRENCH

ROOT = settings.ROOT


def trial(client, text, **body):
    r = client.post("/api/jury", json={"text": text, **body})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(x) for x in r.text.splitlines()]


# ---------- the stream ----------
def test_stream_order_start_then_twenty_jurors_in_seed_order_then_summary(client):
    ev = trial(client, AI_ESSAY)
    assert [e["type"] for e in ev] == ["start"] + ["juror"] * 20 + ["summary"]
    assert [e["seed"] for e in ev[1:21]] == list(range(42, 62)) and [e["i"] for e in ev[1:21]] == list(range(20))
    start = ev[0]
    assert start["jurors"] == 20 and start["typos"] is None and start["precomputed"] is False and start["words"] == len(AI_ESSAY.split())
    assert start["scale"]["val_humans"] == 2291 and start["scale"]["flag_line"] > start["scale"]["above_usual_line"]


def test_marks_carry_p_and_position_on_the_common_scale_not_the_logit(client):
    ev = trial(client, AI_ESSAY)
    sc = ev[0]["scale"]
    for e in ev[1:21]:
        assert set(e) >= {"seed", "p", "position", "zone", "at_cap", "ensemble_member"} and "logit" not in e
        assert 0 < e["p"] <= 1 and e["position"] == pytest.approx(-__import__("math").log10(e["p"]))
        assert e["zone"] == "flagged" and e["position"] >= sc["flag_line"] and e["position"] <= sc["cap"] + 1e-9
    assert [e["ensemble_member"] for e in ev[1:21]] == [True] * 3 + [False] * 17


def test_summary_counts_match_the_marks_and_the_official_verdict(client):
    for essay, zone, ai in ((AI_ESSAY, "flagged", 20), (STUDENT_ESSAY, "not_flagged", 0)):
        ev = trial(client, essay)
        s = ev[-1]
        tally = {z: sum(e["zone"] == z for e in ev[1:21]) for z in ("flagged", "above_usual", "not_flagged")}
        assert s["counts"] == tally and sum(tally.values()) == 20
        assert s["says_ai"] == ai == tally["flagged"] and s["says_student"] == tally["not_flagged"] and s["unsure"] == tally["above_usual"]
        assert s["official"]["zone"] == zone and [x["seed"] for x in s["official"]["seeds"]] == [42, 43, 44]


def test_the_stream_never_contains_the_essay(client):
    raw = client.post("/api/jury", json={"text": AI_ESSAY, "typos": True}).text
    assert AI_ESSAY[:60] not in raw and "advantages" not in raw


# ---------- refusals: same rules as /api/score, before any stream ----------
def test_refusals_are_ordinary_errors_before_the_stream(client):
    for text, status, code in ((SHORT, 422, "too_short"), (FRENCH, 422, "not_english"), ("word " * 7000, 413, "too_long")):
        r = client.post("/api/jury", json={"text": text})
        assert r.status_code == status and r.json()["code"] == code
        assert r.headers["content-type"].startswith("application/json")


def test_a_trial_costs_more_than_a_score_and_the_rate_limit_applies(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MIN", 3 * settings.JURY_COST)
    for _ in range(3):
        assert client.post("/api/jury", json={"text": STUDENT_ESSAY}).status_code == 200
    r = client.post("/api/jury", json={"text": STUDENT_ESSAY})
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and "retry-after" in r.headers


def test_the_reading_limit_is_reported(client):
    long_ = AI_ESSAY + (" more words" * 700)
    start = trial(client, long_)[0]
    assert start["truncated"] is True and start["tokens_read"] == 512 and start["tokens"] > 512 and start["read_chars"] < len(long_)


def test_it_waits_for_the_model_lock_and_always_releases_it(client, monkeypatch):
    assert main._model_lock.acquire(blocking=False)
    monkeypatch.setattr(settings, "LOCK_WAIT_SECONDS", 0.05)
    try:
        ev = trial(client, AI_ESSAY)
        assert ev == [{"type": "error", "code": "busy", "detail": "The detector is busy with another request. Please try again in a moment."}]
    finally:
        main._model_lock.release()
    assert len(trial(client, AI_ESSAY)) == 22
    assert main._model_lock.acquire(blocking=False)          # the trial gave the lock back
    main._model_lock.release()


def test_a_failure_inside_the_stream_is_one_plain_error_line_and_frees_the_lock(client, jury, monkeypatch):
    monkeypatch.setattr(jury, "logits_of", lambda seed, ids: (_ for _ in ()).throw(RuntimeError("secret " + AI_ESSAY[:30])))
    r = client.post("/api/jury", json={"text": AI_ESSAY})
    last = json.loads(r.text.splitlines()[-1])
    assert last == {"type": "error", "code": "failed", "detail": "The jury could not finish. Please try again."} and AI_ESSAY[:30] not in r.text
    assert main._model_lock.acquire(blocking=False)
    main._model_lock.release()


# ---------- "Re-run the trial": typos ----------
def test_typos_add_words_changed_and_each_jurors_mark_before(client, jury):
    jury.degrade_unless = AI_ESSAY                           # any edited copy of the AI essay scores low
    ev = trial(client, AI_ESSAY, typos=True, seed=7)
    t = ev[0]["typos"]
    assert t["rate"] == settings.JURY_TYPO_RATE == 0.05 and t["seed"] == 7 and t["words_changed"] > 0 and 0 < t["words_changed_share"] < 0.2
    assert all("before" in e and e["before"]["zone"] == "flagged" and e["zone"] == "not_flagged" for e in ev[1:21])
    s = ev[-1]
    assert s["counts"]["not_flagged"] == 20 and s["before"]["says_ai"] == 20 and s["jurors_changed_zone"] == 20 and s["jurors_changed_flag"] == 20
    assert s["official_changed"] is True and s["before"]["official"]["zone"] == "flagged" and s["official"]["zone"] == "not_flagged"


def test_same_seed_same_trial_other_seed_other_typos(client):
    a, b, c = (trial(client, STUDENT_ESSAY, typos=True, seed=s)[0]["typos"] for s in (5, 5, 6))
    assert a == b and a != c


def test_typos_use_the_same_edit_as_the_rewrite_endpoint(client):
    edit = client.post("/api/rewrite", json={"text": STUDENT_ESSAY, "method": "typos5", "seed": 11}).json()
    t = trial(client, STUDENT_ESSAY, typos=True, seed=11)[0]["typos"]
    assert t["words_changed"] == edit["words_changed"]


# ---------- no GPU ----------
@pytest.fixture
def cpu_client(client, monkeypatch):
    monkeypatch.setattr(main, "jury", lambda: FakeJury(live=False))
    return client


def test_without_a_gpu_the_built_in_examples_are_served_from_precomputed_results(cpu_client):
    for ex in results.examples():
        ev = trial(cpu_client, ex["text"])
        assert ev[0]["precomputed"] is True and [e["type"] for e in ev] == ["start"] + ["juror"] * 20 + ["summary"]
    ai = trial(cpu_client, results.examples()[0]["text"])
    assert ai[-1]["says_ai"] == 20 and ai[-1]["official"]["zone"] == "flagged"
    stu = trial(cpu_client, results.examples()[1]["text"])
    assert stu[-1]["says_ai"] == 0 and stu[-1]["official"]["zone"] == "not_flagged"


def test_without_a_gpu_the_re_run_uses_stored_typo_runs_and_says_which(cpu_client):
    ex = results.examples()[0]["text"]
    ev = trial(cpu_client, ex, typos=True, seed=43)
    assert ev[0]["typos"]["seed"] == 43 and "before" in ev[1] and ev[0]["precomputed"] is True
    far = trial(cpu_client, ex, typos=True, seed=1234)[0]["typos"]
    assert far["requested_seed"] == 1234 and far["seed"] in settings.JURY_PRECOMPUTED_SEEDS


def test_without_a_gpu_any_other_essay_is_refused_in_plain_words(cpu_client):
    r = cpu_client.post("/api/jury", json={"text": AI_ESSAY + " Another sentence added to the end of this essay so it differs."})
    assert r.status_code == 503 and r.json()["code"] == "needs_gpu" and "needs a GPU" in r.json()["detail"]
    assert cpu_client.get("/api/meta").json()["jury"]["live"] is False


def test_the_precomputed_file_holds_hashes_not_essay_text():
    raw = settings.JURY_PRECOMPUTED.read_text()
    assert all(ex["text"][:80] not in raw for ex in results.examples())
    assert set(json.loads(raw)["examples"]) == {jury_api.digest(ex["text"]) for ex in results.examples()}


def test_the_official_verdict_still_works_on_the_cpu_path(cpu_client):
    r = cpu_client.post("/api/score", json={"text": AI_ESSAY}).json()
    assert r["verdict"]["zone"] == "flagged"


# ---------- official verdict on the existing endpoints ----------
def test_score_returns_the_ensemble_verdict_and_keeps_the_old_fields(client):
    r = client.post("/api/score", json={"text": AI_ESSAY}).json()
    assert {"logit", "words", "tokens", "truncated", "read_chars"} <= set(r)
    v = r["verdict"]
    assert v["zone"] == "flagged" and v["explained_by"] == "seed 42" and [s["seed"] for s in v["seeds"]] == [42, 43, 44] and 0 < v["p"] <= 0.00235
    assert client.post("/api/score", json={"text": STUDENT_ESSAY}).json()["verdict"]["zone"] == "not_flagged"


def test_rewrite_scores_the_edited_essay_with_a_verdict_too(client):
    r = client.post("/api/rewrite", json={"text": STUDENT_ESSAY, "method": "typos5"}).json()
    assert r["verdict"]["zone"] in {"flagged", "above_usual", "not_flagged"}


def test_batch_reports_each_essays_zone_and_jurors_flagging(client, monkeypatch):
    files = [("files", ("ai.txt", AI_ESSAY.encode(), "text/plain")), ("files", ("stu.txt", STUDENT_ESSAY.encode(), "text/plain")),
             ("files", ("short.txt", SHORT.encode(), "text/plain"))]
    live = client.post("/api/batch", files=files).json()["results"]
    assert [i["verdict"]["zone"] for i in live[:2]] == ["flagged", "not_flagged"] and [i["jurors_flagging"] for i in live[:2]] == [20, 0]
    assert live[2]["error"]["code"] == "too_short" and "verdict" not in live[2]
    monkeypatch.setattr(main, "jury", lambda: FakeJury(live=False))          # now the same server without a GPU
    cpu = client.post("/api/batch", files=files).json()["results"]
    assert [i["verdict"]["zone"] for i in cpu[:2]] == ["flagged", "not_flagged"] and [i["jurors_flagging"] for i in cpu[:2]] == [None, None]


# ---------- /api/meta ----------
def test_meta_exposes_the_official_figures_from_the_results_files(client):
    m = client.get("/api/meta").json()
    o = m["official"]
    assert o["students_unseen_topics"]["flagged"] == {"value": 0.0070, "lo": 0.0048, "hi": 0.0095}          # fractions, not percentages
    assert o["students_unseen_topics"]["by_topic"]["Summer projects"]["flagged"]["value"] == 0.0160
    assert o["ai_unseen_generators"]["flagged"] == {"value": 0.9492, "lo": 0.9395, "hi": 0.9580}
    assert o["p_ai_given_zone"]["34.6% (the dataset)"]["above_usual"]["value"] == 0.308 and o["p_ai_given_zone"]["10%"]["above_usual"]["value"] == 0.086
    assert m["api_version"] == 3 and m["thresholds"]["standard"] == pytest.approx(4.666, abs=1e-3)       # the existing page keeps working


def test_meta_jury_statistics_are_the_numbers_in_the_summary_file(client):
    j = client.get("/api/meta").json()["jury"]
    assert j["live"] is True and j["jurors"] == 20 and j["scale"]["val_humans"] == 2291 and len(j["per_juror"]) == 20 and j["typo_rate"] == 0.05
    s = pd.read_csv(ROOT / "results" / "22_jury_summary.csv")
    def file_value(stat, pop, group, metric):
        return float(s[(s.stat == stat) & (s.population == pop) & (s.group == group) & (s.metric == metric)].value.iloc[0])
    for stat, pop, group, metric in (("S3", "test_humans", "all20", "share_ge1"), ("S3", "heldout_prompt_humans", "all20", "share_all"),
                                     ("S3", "heldout_generator_AI [descriptive]", "all20", "share_all"), ("S5", "heldout_generator_AI [descriptive]", "all20", "ceiling_ai_not_unanimous"),
                                     ("S7", "test_AI", "all20", "spearman_mean"), ("S8", "test+heldout_prompt", "seed42", "essays_changing_p95")):
        assert j["statistics"][stat][pop][group][metric]["value"] == pytest.approx(file_value(stat, pop, group, metric))
    assert set(j["statistics"]["S1"]["test_AI"]) == {"all20"}


def test_meta_attacks_final_gives_students_above_usual_next_to_the_ai_numbers(client):
    a = client.get("/api/meta").json()["jury"]["attacks_final"]
    r = pd.read_csv(ROOT / "results" / "22b_attack_final.csv")
    def row(group, attack):
        return r[(r.group == group) & (r.attack == attack)].iloc[0]
    assert a["ai_test"]["attacks"]["typos5"]["flip"] == pytest.approx(row("AI, test", "typos 5%").flip_pct / 100, abs=1e-6)
    assert a["ai_unseen_generators"]["descriptive"] is True and a["ai_test"]["descriptive"] is False
    st = a["students_test"]["attacks"]
    assert st["original"]["above_usual"] == 0.0 and st["t5"]["above_usual"] == 0.03       # students land in "above usual" too
    assert a["students_unseen_prompts"]["attacks"]["original"]["above_usual"] == pytest.approx(0.0433, abs=1e-4)


def test_every_share_in_the_new_meta_blocks_is_a_fraction(client):
    """One unit for the new blocks: fractions between 0 and 1 (counts, logits and correlations are named as such)."""
    m = client.get("/api/meta").json()
    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from walk(v, f"{path}/{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yield from walk(v, f"{path}[{i}]")
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            yield path, x
    for path, v in walk(m["official"]):
        if "/n" not in path.split("/")[-1:] and not path.endswith("/n"):
            assert 0 <= v <= 1 or "tau" in path, path
    for group in m["jury"]["attacks_final"].values():
        for attack in group["attacks"].values():
            for k in ("flagged", "flagged_lo", "flagged_hi", "flagged_or_above", "above_usual", "flip", "flip_lo", "flip_hi", "words_changed"):
                assert 0 <= attack[k] <= 1, k
    assert "pct" not in str(list(m["jury"]["attacks_final"]["ai_test"]["attacks"]["typos5"]))
    assert all(0 <= j["detect_test_ai"] <= 1 and 0 <= j["flag_test_students"] <= 1 for j in m["jury"]["per_juror"])
    assert all(0 <= v["value"] <= 1 for pop in m["jury"]["statistics"]["S3"].values() for g in pop.values() for v in g.values())


def test_meta_attacks_final_says_where_lost_flags_went(client):
    a = client.get("/api/meta").json()["jury"]["attacks_final"]
    t5 = a["ai_test"]["attacks"]["typos5"]
    assert (t5["flip_k"], t5["flip_to_above_usual"], t5["flip_to_not_flagged"]) == (12, 12, 0)
    g5 = a["ai_unseen_generators"]["attacks"]["typos5"]
    assert (g5["flip_k"], g5["flip_to_above_usual"], g5["flip_to_not_flagged"]) == (82, 73, 9)


def test_the_front_end_test_fixture_still_matches_the_api():
    """frontend/src/lib/meta.fixture.json is what npm test reads; regenerate it with scripts/export_meta_fixture.py when results change."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("export_meta_fixture", ROOT / "scripts" / "export_meta_fixture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert json.loads(json.dumps(mod.trimmed(), sort_keys=True)) == json.loads(mod.OUT.read_text())


def test_a_visitor_who_leaves_mid_trial_cannot_leave_the_model_locked(client, jury):
    """The trial runs in its own thread that holds the lock while it computes and always lets it go, so a closed tab frees the server."""
    import time
    with client.stream("POST", "/api/jury", json={"text": AI_ESSAY}) as r:
        next(r.iter_lines())                        # read one line, then walk away without reading the rest
    for _ in range(100):
        if main._model_lock.acquire(blocking=False):
            main._model_lock.release()
            break
        time.sleep(0.05)
    else:
        raise AssertionError("the model lock is still held after the client left")
    assert len(trial(client, AI_ESSAY)) == 22


def test_a_visitor_who_leaves_mid_trial_cannot_leave_the_model_locked(client, jury):
    """The trial runs in its own thread that holds the lock while it computes and always lets it go, so a closed tab frees the server."""
    import time
    with client.stream("POST", "/api/jury", json={"text": AI_ESSAY}) as r:
        next(r.iter_lines())                        # read one line, then walk away without reading the rest
    for _ in range(100):
        if main._model_lock.acquire(blocking=False):
            main._model_lock.release()
            break
        time.sleep(0.05)
    else:
        raise AssertionError("the model lock is still held after the client left")
    assert len(trial(client, AI_ESSAY)) == 22
