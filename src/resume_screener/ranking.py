"""Rank scored resumes and label each score with a verdict band.

Ranking is highest score first, with the candidate name as a stable
tie-break so equal scores always order the same way. Verdict bands are
labels only — they never change the order — and their thresholds are
documented here so a report reader can interpret them:

* >= 80: Strong match
* >= 60: Good match
* >= 40: Partial match
* < 40:  Weak match
"""

from __future__ import annotations

from .scoring import Score

__all__ = ["rank", "verdict"]


def verdict(total: float) -> str:
    """Verdict band for a 0–100 total."""
    if total >= 80:
        return "Strong match"
    if total >= 60:
        return "Good match"
    if total >= 40:
        return "Partial match"
    return "Weak match"


def rank(scores: list[Score]) -> list[Score]:
    """Sort scores best-first, breaking ties by candidate name."""
    return sorted(
        scores,
        key=lambda s: (-s.total, (s.resume.name or s.resume.source).lower()),
    )
