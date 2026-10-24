"""Tests for contact, section, skill and experience parsing."""

from datetime import date

from resume_screener.parser import (
    extract_contact,
    extract_skills,
    experience_years,
    parse_resume,
    split_sections,
)

SAMPLE = """Asha Patel
asha.patel@example.com | +91 98765 43210
linkedin.com/in/ashapatel

Summary
Backend engineer.

Work Experience
Senior Backend Engineer, Northwind Labs
Jan 2021 - Dec 2023
Backend Engineer, River Systems
Jun 2019 - Dec 2020

Technical Skills
Python, FastAPI, Python, Docker
"""


def test_contact_extraction():
    contact = extract_contact(SAMPLE)
    assert contact.name == "Asha Patel"
    assert contact.email == "asha.patel@example.com"
    assert contact.phone == "+91 98765 43210"
    assert contact.linkedin == "linkedin.com/in/ashapatel"


def test_name_skips_contact_lines():
    text = "asha@example.com\n+91 98765 43210\nRahul Verma\n"
    assert extract_contact(text).name == "Rahul Verma"


def test_section_synonyms_map_to_canonical_keys():
    sections = split_sections(SAMPLE)
    assert "experience" in sections
    assert "skills" in sections
    assert "summary" in sections
    assert "Northwind Labs" in sections["experience"]


def test_unknown_all_caps_heading_preserved():
    sections = split_sections("VOLUNTEERING\nMentored students.\n")
    assert sections == {"volunteering": "Mentored students."}


def test_preamble_is_not_a_section():
    sections = split_sections("Asha Patel\nasha@example.com\n\nSkills\nPython\n")
    assert sections == {"skills": "Python"}


def test_skills_split_and_deduped():
    assert extract_skills("Python, FastAPI; Docker\nPython") == [
        "Python",
        "FastAPI",
        "Docker",
    ]


def test_experience_years_month_ranges():
    text = "Jan 2021 - Dec 2023\nJun 2019 - Dec 2020\n"
    # 36 + 19 months = 55 months = 4.6 years.
    assert experience_years(text, as_of=date(2026, 1, 1)) == 4.6


def test_experience_years_present_uses_as_of():
    text = "Jan 2026 - Present\n"
    assert experience_years(text, as_of=date(2026, 6, 1)) == 0.5


def test_parse_resume_end_to_end():
    resume = parse_resume(SAMPLE, as_of=date(2026, 1, 1))
    assert resume.name == "Asha Patel"
    assert resume.skills == ["Python", "FastAPI", "Docker"]
    assert resume.experience_years == 4.6
    assert resume.section("missing", "fallback") == "fallback"


def test_parse_empty_resume():
    resume = parse_resume("")
    assert resume.name == ""
    assert resume.skills == []
    assert resume.experience_years == 0.0
