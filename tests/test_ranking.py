"""Tests for ranking order, tie-breaks, and verdict bands."""

from resume_screener.models import ContactInfo, Resume
from resume_screener.ranking import rank, verdict
from resume_screener.scoring import Score


def _score(name, total):
    resume = Resume(source=f"{name}.txt", contact=ContactInfo(name=name))
    return Score(resume=resume, job_title="Role", total=total)


def test_rank_orders_best_first():
    scores = [_score("Low", 40.0), _score("High", 90.0), _score("Mid", 65.0)]
    assert [s.resume.name for s in rank(scores)] == ["High", "Mid", "Low"]


def test_rank_breaks_ties_by_name():
    scores = [_score("Zoe", 70.0), _score("Amy", 70.0)]
    assert [s.resume.name for s in rank(scores)] == ["Amy", "Zoe"]


def test_verdict_bands():
    assert verdict(80.0) == "Strong match"
    assert verdict(79.9) == "Good match"
    assert verdict(60.0) == "Good match"
    assert verdict(40.0) == "Partial match"
    assert verdict(39.9) == "Weak match"
    assert verdict(0.0) == "Weak match"
