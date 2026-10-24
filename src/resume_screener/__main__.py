"""Allow ``python -m resume_screener`` as the CLI entry point."""

from resume_screener.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
