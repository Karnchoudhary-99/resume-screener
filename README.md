# AI Resume Screener

Parse resumes, score candidates against a job description, and rank
them — with the reasons for each score visible, not just a number.

## Roadmap

- [x] Project scaffold (pyproject, src layout, CI)
- [x] Resume parsing (text/PDF/DOCX extraction, section detection)
- [x] Scoring engine (skill match, experience fit, education fit)
- [x] Ranking + explanations, CLI report
- [x] Screening reports (shortlist, CSV/Markdown/JSON export, anonymized review)
- [x] Directory screening (score a whole folder in one call)
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

## Screening reports

The printed ranking is for a quick look; a hiring loop usually wants a
file it can forward and a shortlist, not the whole pile:

```bash
python -m resume_screener score --job examples/job.json \
  --min-score 60 \
  --report-csv screening-report.csv \
  --report-md screening-report.md \
  --report-json screening-report.json \
  examples/sample_resume.txt examples/sample_junior.txt
```

- **`--min-score N`** keeps only candidates scoring at least `N`
  (0–100, inclusive). It applies before `--top` and before every
  report file, so the files always match what the CLI printed.
- **CSV** (`--report-csv`) has one row per candidate, best first:
  rank, name, email, score, verdict, experience years, one percentage
  column per component (blank when the job does not define that
  component — blank means "not scored", never "scored zero"), and
  matched / missing / preferred skills (`;`-separated).
- **Markdown** (`--report-md`) opens with a summary (candidate count,
  mean score, verdict distribution), then a ranked table, then one
  section per candidate with the component breakdown and the reasons
  behind the score.
- **JSON** (`--report-json`) is the same payload as `--format json`,
  written to a file instead of stdout.
- **`--anonymize`** strips names, emails, phones, profile links and
  source paths from the output and reports, relabelling candidates
  `Candidate 1, 2, …` in ranked order — for a blind first review. It
  never changes scores or order, only identities.

See `docs/sample-report.md` for a report generated from the bundled
samples (senior sample only clears the `--min-score 60` bar).

## Screening a folder

Pass a directory instead of individual files and every supported
resume inside it (`.txt`, `.md`, `.docx`, `.pdf`) is scored, sorted
by file name. Other files in the folder are ignored; an empty folder
is an error, so a typo never silently scores nothing:

```bash
python -m resume_screener score --job examples/job.json applicants/
```

Directories and files mix freely, and the same resume given twice
(by any path spelling) is scored once.

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

MIT
