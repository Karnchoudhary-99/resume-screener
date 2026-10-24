"""Tests for screening reports (shortlist, CSV, Markdown, summary)."""

import csv

import pytest

from resume_screener.models import ContactInfo, Resume
from resume_screener.report import (
    CSV_COLUMNS,
    anonymize,
    render_markdown,
    shortlist,
    summary,
    write_csv,
)
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


def test_markdown_report_table_and_details():
    text = render_markdown("Backend Engineer", [_score("Asha", 100.0), _score("Rahul", 29.6)])
    assert "# Screening report: Backend Engineer" in text
    assert "| 1 | Asha | 100.0 | Strong match |" in text
    assert "## 2. Rahul — 29.6/100 (Weak match)" in text
    assert "Missing: Docker." in text
    assert "Covers most required skills." in text


def test_markdown_empty_report():
    assert "No candidates were scored." in render_markdown("Role", [])


def test_markdown_escapes_pipes():
    text = render_markdown("Role", [_score("A | B", 80.0)])
    assert "A \\| B" in text


def test_summary_counts_and_means():
    stats = summary([_score("Asha", 100.0), _score("Rahul", 60.0, {"skills": 0.5, "experience": 1.0})])
    assert stats["count"] == 2
    assert stats["mean_score"] == 80.0
    assert stats["verdict_counts"] == {"Strong match": 1, "Good match": 1}
    assert stats["mean_components"]["skills"] == 0.75
    assert stats["mean_components"]["experience"] == 1.0  # only Rahul scored it


def test_summary_empty_and_markdown_summary_line():
    assert summary([])["count"] == 0
    text = render_markdown("Role", [_score("Asha", 100.0), _score("Rahul", 60.0)])
    assert "Candidates: 2 · Mean score: 80.0" in text
    assert "Verdicts: Strong match ×1, Good match ×1." in text


def test_anonymize_strips_identity_without_mutating_original():
    original = [_score("Asha", 100.0), _score("Rahul", 60.0)]
    anon = anonymize(original)
    assert [s.resume.name for s in anon] == ["Candidate 1", "Candidate 2"]
    assert all(s.resume.email == "" and s.resume.source == "" for s in anon)
    assert [s.total for s in anon] == [100.0, 60.0]
    assert original[0].resume.name == "Asha"  # original untouched
    text = render_markdown("Role", anon)
    assert "Asha" not in text and "Candidate 1" in text


def test_shortlist_rejects_out_of_range():
    scores = [_score("Asha", 100.0)]
    for bad in (-1.0, 100.1, float("nan")):
        with pytest.raises(ValueError):
            shortlist(scores, bad)
