"""Screening reports: shortlists and shareable report files.

The score CLI prints a ranking, but a hiring loop needs something it can
file away and forward: a shortlist (who clears the bar) and a report file
(CSV for a spreadsheet, Markdown for a readable record). This module
keeps both out of the CLI so they are testable on their own.

A shortlist is a threshold filter, nothing more: a candidate clears it
when their total is at least ``min_score``. The threshold is inclusive
— a candidate scoring exactly the bar is in — and it must be a real
0–100 number, otherwise the caller gets a ``ValueError`` instead of a
silently empty or silently full list.
"""

from __future__ import annotations

from .scoring import Score

__all__ = ["shortlist"]


def shortlist(scores: list[Score], min_score: float) -> list[Score]:
    """Return the scores at or above ``min_score``, in the given order.

    The input order is preserved (callers pass an already-ranked list);
    this function only filters, it never re-sorts.
    """
    if min_score != min_score or min_score < 0 or min_score > 100:
        raise ValueError("min_score must be a number between 0 and 100")
    return [s for s in scores if s.total >= min_score]
