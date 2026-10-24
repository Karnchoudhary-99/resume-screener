"""Tests for the parse CLI command."""

import json
from pathlib import Path

import pytest

from resume_screener.cli import main

RESUME = "Asha Patel\nasha@example.com\n\nSkills\nPython, Docker\n"


def test_cli_parse_text(tmp_path, capsys):
    p = tmp_path / "resume.txt"
    p.write_text(RESUME)
    assert main(["parse", str(p)]) == 0
    out = capsys.readouterr().out
    assert "Name: Asha Patel" in out
    assert "Skills: Python, Docker" in out


def test_cli_parse_json(tmp_path, capsys):
    p = tmp_path / "resume.txt"
    p.write_text(RESUME)
    assert main(["parse", str(p), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contact"]["name"] == "Asha Patel"
    assert payload["skills"] == ["Python", "Docker"]


def test_cli_parse_missing_file():
    assert main(["parse", "/nonexistent/resume.txt"]) == 1


def test_cli_parse_unsupported_format(tmp_path):
    p = tmp_path / "resume.odt"
    p.write_text("x")
    assert main(["parse", str(p)]) == 1


def test_cli_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"
