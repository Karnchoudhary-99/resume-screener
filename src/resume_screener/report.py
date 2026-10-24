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

import csv

from .ranking import verdict
from .scoring import Score

__all__ = ["render_markdown", "shortlist", "write_csv", "write_markdown"]

#: CSV columns, in order. Component columns are 0–100 percentages and
#: are left blank when the job does not define that component, so a
#: blank always means "not scored", never "scored zero".
CSV_COLUMNS = [
    "rank", "name", "email", "score", "verdict", "experience_years",
    "skills_pct", "experience_pct", "education_pct",
    "matched_skills", "missing_skills", "preferred_matched",
]


def shortlist(scores: list[Score], min_score: float) -> list[Score]:
    """Return the scores at or above ``min_score``, in the given order.

    The input order is preserved (callers pass an already-ranked list);
    this function only filters, it never re-sorts.
    """
    if min_score != min_score or min_score < 0 or min_score > 100:
        raise ValueError("min_score must be a number between 0 and 100")
    return [s for s in scores if s.total >= min_score]


def _pct(components: dict[str, float], name: str) -> str:
    """A component as a 0–100 string, or blank when not scored."""
    if name not in components:
        return ""
    return f"{components[name] * 100:.1f}"


def _row(rank: int, score: Score) -> dict[str, str]:
    """One CSV row for a ranked score; the csv module does the quoting."""
    return {
        "rank": str(rank),
        "name": score.resume.name or score.resume.source,
        "email": score.resume.email,
        "score": f"{score.total:.1f}",
        "verdict": verdict(score.total),
        "experience_years": f"{score.resume.experience_years:g}",
        "skills_pct": _pct(score.components, "skills"),
        "experience_pct": _pct(score.components, "experience"),
        "education_pct": _pct(score.components, "education"),
        "matched_skills": "; ".join(score.matched_skills),
        "missing_skills": "; ".join(score.missing_skills),
        "preferred_matched": "; ".join(score.preferred_matched),
    }


def _cell(text: str) -> str:
    """Escape a value for a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(job_title: str, scores: list[Score]) -> str:
    """Render ranked scores as a Markdown screening report.

    A ranked table first (the short version a manager scans), then one
    section per candidate with the reasons behind the score — the same
    explanations the CLI prints, so the file never disagrees with it.
    """
    lines = [f"# Screening report: {job_title}", ""]
    if not scores:
        lines.append("No candidates were scored.")
        return "\n".join(lines) + "\n"
    lines.append("| Rank | Candidate | Score | Verdict | Experience |")
    lines.append("| --- | --- | --- | --- | --- |")
    for rank, score in enumerate(scores, start=1):
        name = _cell(score.resume.name or score.resume.source)
        lines.append(
            f"| {rank} | {name} | {score.total:.1f} | "
            f"{verdict(score.total)} | {score.resume.experience_years:g} years |"
        )
    for rank, score in enumerate(scores, start=1):
        name = score.resume.name or score.resume.source
        lines.append("")
        lines.append(f"## {rank}. {name} — {score.total:.1f}/100 "
                     f"({verdict(score.total)})")
        if score.components:
            breakdown = ", ".join(
                f"{k} {v * 100:.0f}%" for k, v in score.components.items()
            )
            lines.append(f"Components: {breakdown}.")
        if score.matched_skills:
            lines.append(f"Matched: {', '.join(score.matched_skills)}.")
        if score.missing_skills:
            lines.append(f"Missing: {', '.join(score.missing_skills)}.")
        for line in score.explanations:
            lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def write_markdown(job_title: str, scores: list[Score], path: str) -> None:
    """Write :func:`render_markdown` output to ``path``."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_markdown(job_title, scores))


def write_csv(scores: list[Score], path: str) -> None:
    """Write ranked scores to ``path`` as CSV, best first, ranked 1..n."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for rank, score in enumerate(scores, start=1):
            writer.writerow(_row(rank, score))
