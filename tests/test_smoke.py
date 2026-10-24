from resume_screener.cli import main


def test_cli_exits_zero():
    assert main(["--version"]) == 0
