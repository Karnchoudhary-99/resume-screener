# AI Resume Screener

Parse resumes, score candidates against a job description, and rank
them — with the reasons for each score visible, not just a number.

## Roadmap

- [x] Project scaffold (pyproject, src layout, CI)
- [x] Resume parsing (text/PDF/DOCX extraction, section detection)
- [ ] Scoring engine (skill match, experience fit, education fit)
- [ ] Ranking + explanations, CLI report
- [ ] Tests, README polish, then self-review checklist, then public

## Quick start

```bash
pip install -e .
python -m resume_screener parse examples/sample_resume.txt
python -m resume_screener parse resume.pdf --format json
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
