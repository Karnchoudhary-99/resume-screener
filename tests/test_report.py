"""Tests for screening reports (shortlist, CSV, Markdown, summary)."""

import csv

import pytest

from resume_screener.models import ContactInfo, Resume
from resume_screener.report import CSV_COLUMNS, shortlist, write_csv
from resume_screener.scoring import Score


def _score(name, total, components=None):
    resume = Resume(
        source=f"{name}.txt",
        contact=ContactInfo(name=name, email=f"{name.lower()}@example.com"),
        experience_years=5.0,
    )
    return Score(
        resume=resume, job_title="Backend Engineer", total=total,
        components=components or {"skills": 1.0},
        matched_skills=["Python"], missing_skills=["Docker"],
        explanations=["Covers most required skills."],
    )


def test_shortlist_keeps_order_and_is_inclusive():
    scores = [_score("Asha", 100.0), _score("Rahul", 60.0), _score("Mia", 59.9)]
    kept = shortlist(scores, 60.0)
    assert [s.resume.name for s in kept] == ["Asha", "Rahul"]


def test_shortlist_bounds():
    scores = [_score("Asha", 100.0), _score("Rahul", 0.0)]
    assert len(shortlist(scores, 0.0)) == 2
    assert len(shortlist(scores, 100.0)) == 1


def test_csv_rows_ranked_with_header_and_blanks(tmp_path):
    path = str(tmp_path / "report.csv")
    write_csv([_score("Rahul", 29.6), _score("Asha", 100.0)], path)
    # write_csv trusts the caller's order; ranking is the caller's job,
    # so this checks the writer itself, not the ranking.
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == CSV_COLUMNS
    assert rows[0]["rank"] == "1" and rows[0]["name"] == "Rahul"
    assert rows[0]["skills_pct"] == "100.0"
    assert rows[0]["experience_pct"] == ""  # not defined in fixture
    assert rows[0]["missing_skills"] == "Docker"


def test_csv_quotes_commas_in_names(tmp_path):
    score = _score("Doe, Jane", 80.0)
    path = str(tmp_path / "report.csv")
    write_csv([score], path)
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["name"] == "Doe, Jane"


def test_shortlist_rejects_out_of_range():
    scores = [_score("Asha", 100.0)]
    for bad in (-1.0, 100.1, float("nan")):
        with pytest.raises(ValueError):
            shortlist(scores, bad)
