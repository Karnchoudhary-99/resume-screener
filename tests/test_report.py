"""Tests for screening reports (shortlist, CSV, Markdown, summary)."""

import csv

import pytest

from resume_screener.models import ContactInfo, Resume
from resume_screener.report import shortlist
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


def test_shortlist_rejects_out_of_range():
    scores = [_score("Asha", 100.0)]
    for bad in (-1.0, 100.1, float("nan")):
        with pytest.raises(ValueError):
            shortlist(scores, bad)
