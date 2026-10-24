# AI Resume Screener

Parse resumes, score candidates against a job description, and rank
them — with the reasons for each score visible, not just a number.

## Roadmap

- [x] Project scaffold (pyproject, src layout, CI)
- [x] Resume parsing (text/PDF/DOCX extraction, section detection)
- [x] Scoring engine (skill match, experience fit, education fit)
- [x] Ranking + explanations, CLI report
- [ ] Tests, README polish, then self-review checklist, then public

## Quick start

```bash
pip install -e .
python -m resume_screener parse examples/sample_resume.txt
python -m resume_screener parse resume.pdf --format json
python -m resume_screener score --job examples/job.json examples/sample_resume.txt examples/sample_junior.txt
```

## Scoring

A job is a JSON file (`title`, `required_skills`, `preferred_skills`,
`min_years`, `education_keywords` — see `examples/job.json`). Each
candidate gets a 0–100 score plus the reasons behind it:

- **Skills (55%):** required skills count 70%, preferred 30%. Skill
  names are normalised (`Postgres` → `PostgreSQL`, `JS` →
  `JavaScript`), and a skill named only in a project's description
  still counts — word-boundary matching, so `Go` never matches `good`.
- **Experience (25%):** linear up to the minimum, capped above it.
- **Education (20%):** 1.0 if any keyword appears in the education
  section, else 0.0.
- **Only defined components count:** a job with no education
  requirement does not score education at all — weights renormalise
  over the components present.

Ranking is best-first with the candidate name as tie-break; verdict
bands are ≥80 Strong, ≥60 Good, ≥40 Partial, below that Weak. Try it:

```
1. Asha Patel — 100.0/100 (Strong match)
2. Rahul Verma — 29.6/100 (Weak match)
   Missing: FastAPI, PostgreSQL, Docker
```

## Parsing

Parsing is stdlib-only — no third-party dependencies:

- **Formats:** `.txt`, `.md`, `.docx` (unzipped `word/document.xml`),
  and text-based `.pdf` (Flate streams, `Tj`/`TJ` operators).
  Scanned/image PDFs have no text layer and parse as empty — the
  tool reports that honestly instead of guessing.
- **Contact:** name (first name-like header line), email, phone,
  LinkedIn and GitHub profile links.
- **Sections:** headings map to canonical keys (`Work Experience` →
  `experience`, `Technical Skills` → `skills`, …); unknown ALL-CAPS
  headings are kept under their own slug, not dropped.
- **Skills:** the skills section split on commas/semicolons/bullets,
  de-duplicated, order kept.
- **Experience:** date ranges in the experience section summed by
  month (`Jan 2021 - Present` uses today's date; pass `as_of` in code
  for deterministic results).

## License

## License

MIT
