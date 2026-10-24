"""Placeholder CLI — parsing and scoring land in the next session."""

import argparse


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="resume-screener")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)
    if args.version:
        from resume_screener import __version__

        print(__version__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
