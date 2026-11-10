import pytest

from api import results, settings


def test_thresholds_match_the_csv_row_for_row():
    t = results.thresholds()
    assert set(t) == {"strict", "standard"} and t["strict"] > t["standard"]


def test_worst_topic_is_derived_not_typed_in():
    w = results.rates()["standard"]["worst_topic"]
    assert w["topic"] == "Summer projects" and w["percent"] == pytest.approx(7.7, abs=0.05)


def test_example_labels_follow_the_titles():
    assert [e["label"] for e in results.examples()] == ["ai", "human", "human", "human", "ai"]


def test_every_file_the_page_quotes_exists():
    for name in ("09_thresholds.csv", "09_threshold_rates.csv", "13_attack.csv", "14_errors.csv"):
        assert (settings.RESULTS / name).exists()
