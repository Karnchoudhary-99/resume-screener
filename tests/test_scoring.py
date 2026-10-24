"""Tests for the scoring engine: aliases, components, weighting."""

from resume_screener.job import JobDescription
from resume_screener.models import ContactInfo, Resume
from resume_screener.scoring import normalize_skill, score_resume


def _resume(skills, years, education=""):
    sections = {}
    if education:
        sections["education"] = education
    return Resume(
        source="test.txt",
        contact=ContactInfo(name="Test Candidate"),
        sections=sections,
        skills=skills,
        experience_years=years,
    )


JOB = JobDescription(
    title="Backend Engineer",
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Redis"],
    min_years=4,
    education_keywords=["bca"],
)


def test_normalize_skill_aliases():
    assert normalize_skill("JS") == "javascript"
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("  Python  ") == "python"
    assert normalize_skill("C++") == "c++"


def test_full_match_scores_100():
    resume = _resume(["Python", "FastAPI", "PostgreSQL", "Redis"], 5, "BCA")
    score = score_resume(resume, JOB)
    assert score.total == 100.0
    assert score.components == {"skills": 1.0, "experience": 1.0, "education": 1.0}
    assert score.missing_skills == []
    assert "Covers every required skill." in score.explanations


def test_missing_skills_and_short_experience_lower_score():
    resume = _resume(["Python"], 2, "BCA")
    score = score_resume(resume, JOB)
    # skills: 0.7 * 1/3 + 0.3 * 0 = 0.233; experience: 0.5; education: 1.0
    assert score.total == round((0.233 * 0.55 + 0.5 * 0.25 + 1.0 * 0.20) * 100, 1)
    assert score.missing_skills == ["FastAPI", "PostgreSQL"]
    assert any("below the 4-year minimum" in e for e in score.explanations)


def test_components_the_job_does_not_define_are_skipped():
    job = JobDescription(required_skills=["Python"])
    resume = _resume(["Python"], 0)
    score = score_resume(resume, job)
    assert score.components == {"skills": 1.0}
    assert score.total == 100.0  # weight renormalised to the one component


def test_empty_job_scores_zero_with_explanation():
    score = score_resume(_resume([], 0), JobDescription())
    assert score.total == 0.0
    assert score.components == {}
    assert score.explanations


def test_skill_named_only_in_projects_still_matches():
    resume = Resume(
        source="test.txt",
        contact=ContactInfo(name="Proj Only"),
        sections={"projects": "Built a dashboard in Python and FastAPI."},
        skills=[],
        experience_years=0,
    )
    job = JobDescription(required_skills=["Python", "FastAPI", "Docker"])
    score = score_resume(resume, job)
    assert score.matched_skills == ["Python", "FastAPI"]
    assert score.missing_skills == ["Docker"]


def test_go_does_not_match_the_word_good():
    resume = Resume(
        source="test.txt",
        contact=ContactInfo(name="Good Communicator"),
        sections={"summary": "Good communicator and team player."},
        skills=[],
        experience_years=0,
    )
    score = score_resume(resume, JobDescription(required_skills=["Go"]))
    assert score.missing_skills == ["Go"]


def test_education_mismatch_scores_zero_for_that_component():
    resume = _resume(["Python", "FastAPI", "PostgreSQL", "Redis"], 5, "MBA")
    score = score_resume(resume, JOB)
    assert score.components["education"] == 0.0
    assert any("does not mention" in e for e in score.explanations)
