"""A job description: the criteria a resume is scored against.

A job is plain data — no scoring logic lives here — so it can be loaded
from JSON, built in code, or (later) parsed from a job posting without
touching the scorer. Scoring reads a ``JobDescription`` plus a parsed
``Resume`` and nothing else.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["JobDescription", "load_job"]


@dataclass
class JobDescription:
    """What the role asks for. Empty lists mean 'no requirement'."""

    title: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    # Minimum years of experience; None means experience is not scored.
    min_years: float | None = None
    # Degree/field keywords matched against the education section, e.g.
    # ["bca", "bachelor"]. Empty means education is not scored.
    education_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "JobDescription":
        """Build a job from a plain dict (e.g. parsed JSON)."""
        if not isinstance(data, dict):
            raise ValueError("job description must be a JSON object")
        skills = data.get("required_skills", [])
        preferred = data.get("preferred_skills", [])
        education = data.get("education_keywords", [])
        for name, value in (
            ("required_skills", skills),
            ("preferred_skills", preferred),
            ("education_keywords", education),
        ):
            if not isinstance(value, list) or not all(
                isinstance(s, str) for s in value
            ):
                raise ValueError(f"job field {name!r} must be a list of strings")
        min_years = data.get("min_years")
        if min_years is not None:
            try:
                min_years = float(min_years)
            except (TypeError, ValueError) as exc:
                raise ValueError("job field 'min_years' must be a number") from exc
            if min_years < 0:
                raise ValueError("job field 'min_years' must not be negative")
        title = data.get("title", "")
        if not isinstance(title, str):
            raise ValueError("job field 'title' must be a string")
        return cls(
            title=title,
            required_skills=list(skills),
            preferred_skills=list(preferred),
            min_years=min_years,
            education_keywords=list(education),
        )


def load_job(path: str | Path) -> JobDescription:
    """Load a job description from a JSON file."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"job file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"job file is not valid JSON: {p}") from exc
    return JobDescription.from_dict(data)
