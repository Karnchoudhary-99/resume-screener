"""Score a parsed resume against a job description.

The score is a weighted blend of only the components the job actually
defines — a job with no education requirement does not penalise anyone
for education, and a job with no skill list does not score skills. Each
component is 0.0–1.0, the total is 0–100, and every score carries the
plain-language reasons behind it, so a hiring manager can see *why* a
candidate scored what they did instead of trusting a bare number.

Skill matching is deliberately strict about names but forgiving about
spelling variants: "Postgres" matches "PostgreSQL", "JS" matches
"JavaScript". It does not do fuzzy/embedding similarity — a skill the
resume never names is a miss, and the report says so honestly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .job import JobDescription
from .models import Resume

__all__ = ["Score", "normalize_skill", "score_resume"]

#: Common spelling variants -> canonical skill name (all lowercase).
_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "golang": "go",
    "node": "node.js",
    "nodejs": "node.js",
    "reactjs": "react",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "c++": "c++",
    "cpp": "c++",
    "ml": "machine learning",
    "ai": "artificial intelligence",
}

#: Default component weights; renormalised over present components.
_WEIGHTS = {"skills": 0.55, "experience": 0.25, "education": 0.20}


def normalize_skill(skill: str) -> str:
    """Lowercase, trim, and fold a skill name to its canonical form."""
    cleaned = re.sub(r"\s+", " ", skill.strip().lower())
    cleaned = cleaned.strip(".,;")
    return _ALIASES.get(cleaned, cleaned)


@dataclass
class Score:
    """A resume's score against one job, with its reasons attached."""

    resume: Resume
    job_title: str
    total: float  # 0–100
    # Component name -> 0.0–1.0 score, only for components the job defines.
    components: dict[str, float] = field(default_factory=dict)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    preferred_matched: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)


def _skill_component(resume: Resume, job: JobDescription) -> tuple[float, Score]:
    """Skill score: required skills dominate, preferred skills add up to 30%."""
    have = {normalize_skill(s) for s in resume.skills}
    matched, missing = [], []
    for skill in job.required_skills:
        norm = normalize_skill(skill)
        if norm in have or _skill_mentioned(norm, resume):
            matched.append(skill)
        else:
            missing.append(skill)
    preferred_matched = [
        s for s in job.preferred_skills
        if normalize_skill(s) in have or _skill_mentioned(normalize_skill(s), resume)
    ]
    required_score = len(matched) / len(job.required_skills) if job.required_skills else 1.0
    preferred_score = (
        len(preferred_matched) / len(job.preferred_skills)
        if job.preferred_skills else 1.0
    )
    if job.required_skills and job.preferred_skills:
        total = 0.7 * required_score + 0.3 * preferred_score
    elif job.required_skills:
        total = required_score
    else:
        total = preferred_score
    score = Score(resume=resume, job_title=job.title, total=0.0)
    score.matched_skills = matched
    score.missing_skills = missing
    score.preferred_matched = preferred_matched
    return total, score


def _skill_mentioned(normalized: str, resume: Resume) -> bool:
    """True if a skill name appears in the resume's project/summary text.

    Word-boundary matching avoids "go" matching "good" or "r" matching
    every word, and multi-word skills match as a phrase.
    """
    text = " ".join(resume.sections.values()).lower()
    pattern = r"(?<![a-z0-9.+])" + re.escape(normalized) + r"(?![a-z0-9.+])"
    return re.search(pattern, text) is not None


def _experience_component(resume: Resume, job: JobDescription) -> float:
    """Experience fit: linear up to the minimum, capped at 1.0 above it."""
    assert job.min_years is not None
    if job.min_years == 0:
        return 1.0
    return min(1.0, resume.experience_years / job.min_years)


def _education_component(resume: Resume, job: JobDescription) -> float:
    """Education fit: 1.0 if any keyword appears in the education section."""
    education = resume.section("education").lower()
    keywords = [k.lower() for k in job.education_keywords]
    return 1.0 if any(k in education for k in keywords) else 0.0


def score_resume(resume: Resume, job: JobDescription) -> Score:
    """Score one resume against one job; see the module docstring."""
    components: dict[str, float] = {}
    partial = Score(resume=resume, job_title=job.title, total=0.0)
    if job.required_skills or job.preferred_skills:
        skill_score, partial = _skill_component(resume, job)
        components["skills"] = skill_score
    if job.min_years is not None:
        components["experience"] = _experience_component(resume, job)
    if job.education_keywords:
        components["education"] = _education_component(resume, job)

    if not components:
        partial.explanations = [
            "The job description lists no skills, experience, or education "
            "requirements, so there is nothing to score against."
        ]
        partial.components = {}
        partial.total = 0.0
        return partial

    weight_sum = sum(_WEIGHTS[name] for name in components)
    total = sum(
        components[name] * _WEIGHTS[name] / weight_sum for name in components
    )
    partial.components = {k: round(v, 3) for k, v in components.items()}
    partial.total = round(total * 100, 1)
    partial.explanations = _explain(partial, resume, job)
    return partial


def _explain(score: Score, resume: Resume, job: JobDescription) -> list[str]:
    """Plain-language reasons for a score, strongest evidence first."""
    lines: list[str] = []
    if "skills" in score.components:
        if score.missing_skills:
            lines.append(
                "Missing required skills: " + ", ".join(score.missing_skills) + "."
            )
        elif job.required_skills:
            lines.append("Covers every required skill.")
        if score.preferred_matched:
            lines.append(
                "Also covers preferred skills: "
                + ", ".join(score.preferred_matched)
                + "."
            )
    if "experience" in score.components:
        assert job.min_years is not None
        if resume.experience_years >= job.min_years:
            lines.append(
                f"{resume.experience_years} years of experience meets the "
                f"{job.min_years:g}-year minimum."
            )
        else:
            lines.append(
                f"{resume.experience_years} years of experience is below the "
                f"{job.min_years:g}-year minimum."
            )
    if "education" in score.components:
        if score.components["education"] == 1.0:
            lines.append("Education matches the requested background.")
        else:
            lines.append(
                "Education section does not mention: "
                + ", ".join(job.education_keywords)
                + "."
            )
    return lines
