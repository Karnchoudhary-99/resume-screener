"""Tests for job loading/validation and the score CLI."""

import json

import pytest

from resume_screener.cli import main
from resume_screener.job import JobDescription, load_job

SENIOR = """Asha Patel
asha.patel@example.com

Experience
Senior Backend Engineer, Northwind Labs
Jan 2021 - Present
Built payment APIs.

Education
BCA, State University
2015 - 2019

Skills
Python, FastAPI, PostgreSQL, Docker, Redis, pytest
"""

JUNIOR = """Rahul Verma
rahul.verma@example.com

Education
BCA, City College
2022 - 2025

Skills
Python, HTML, CSS
"""

JOB = {
    "title": "Backend Engineer (Python)",
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "preferred_skills": ["Redis", "pytest"],
    "min_years": 3,
    "education_keywords": ["bca", "bachelor"],
}


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_load_job_round_trip(tmp_path):
    path = _write(tmp_path, "job.json", json.dumps(JOB))
    job = load_job(path)
    assert job.title == "Backend Engineer (Python)"
    assert job.min_years == 3
    assert job.required_skills[0] == "Python"


def test_load_job_rejects_bad_input(tmp_path):
    with pytest.raises(ValueError):
        load_job(_write(tmp_path, "bad.json", "{not json"))
    with pytest.raises(ValueError):
        load_job(_write(tmp_path, "types.json", json.dumps({"required_skills": "Python"})))
    with pytest.raises(ValueError):
        load_job(_write(tmp_path, "neg.json", json.dumps({"min_years": -1})))
    with pytest.raises(FileNotFoundError):
        load_job(tmp_path / "missing.json")


def test_from_dict_defaults():
    job = JobDescription.from_dict({})
    assert job.required_skills == [] and job.min_years is None


def test_score_cli_ranks_senior_first(tmp_path, capsys):
    job = _write(tmp_path, "job.json", json.dumps(JOB))
    senior = _write(tmp_path, "senior.txt", SENIOR)
    junior = _write(tmp_path, "junior.txt", JUNIOR)
    assert main(["score", "--job", job, junior, senior]) == 0
    out = capsys.readouterr().out
    assert out.index("Asha Patel") < out.index("Rahul Verma")
    assert "Strong match" in out
    assert "Missing: FastAPI, PostgreSQL, Docker" in out


def test_score_cli_json_and_top(tmp_path, capsys):
    job = _write(tmp_path, "job.json", json.dumps(JOB))
    senior = _write(tmp_path, "senior.txt", SENIOR)
    junior = _write(tmp_path, "junior.txt", JUNIOR)
    assert main(["score", "--job", job, "--format", "json", "--top", "1", junior, senior]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["name"] == "Asha Patel"
    assert payload[0]["rank"] == 1
    assert payload[0]["score"] == 100.0


def test_score_cli_min_score_filters_and_validates(tmp_path, capsys):
    job = _write(tmp_path, "job.json", json.dumps(JOB))
    senior = _write(tmp_path, "senior.txt", SENIOR)
    junior = _write(tmp_path, "junior.txt", JUNIOR)
    assert main(["score", "--job", job, "--min-score", "60", junior, senior]) == 0
    out = capsys.readouterr().out
    assert "Asha Patel" in out and "Rahul Verma" not in out
    assert main(["score", "--job", job, "--min-score", "101", senior]) == 1
    assert "error" in capsys.readouterr().err


def test_score_cli_report_files_match_filtered_ranking(tmp_path):
    job = _write(tmp_path, "job.json", json.dumps(JOB))
    senior = _write(tmp_path, "senior.txt", SENIOR)
    junior = _write(tmp_path, "junior.txt", JUNIOR)
    csv_path = str(tmp_path / "report.csv")
    md_path = str(tmp_path / "report.md")
    assert main(["score", "--job", job, "--min-score", "60",
                 "--report-csv", csv_path, "--report-md", md_path,
                 junior, senior]) == 0
    csv_text = (tmp_path / "report.csv").read_text()
    assert "Asha Patel" in csv_text and "Rahul Verma" not in csv_text
    md_text = (tmp_path / "report.md").read_text()
    assert "Screening report: Backend Engineer (Python)" in md_text
    assert "Candidates: 1" in md_text


def test_score_cli_missing_job_fails(tmp_path, capsys):
    resume = _write(tmp_path, "r.txt", SENIOR)
    assert main(["score", "--job", str(tmp_path / "nope.json"), resume]) == 1
    assert "error" in capsys.readouterr().err
