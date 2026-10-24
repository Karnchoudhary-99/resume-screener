# AI Resume Screener

Parse resumes, score candidates against a job description, and rank
them — with the reasons for each score visible, not just a number.

## Roadmap

- [x] Project scaffold (pyproject, src layout, CI)
- [ ] Resume parsing (text/PDF/DOCX extraction, section detection)
- [ ] Scoring engine (skill match, experience fit, education fit)
- [ ] Ranking + explanations, CLI report
- [ ] Tests, README polish, then self-review checklist, then public

## Quick start

```bash
pip install -e .
python -m resume_screener --help
```

## License

MIT
