import sys

import pytest

from todex.__main__ import main


def run_main(monkeypatch, argv: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["todex", *argv])
    main()


def test_i_without_t_errors(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, ["-i", str(tmp_path)])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "-t" in err or "tokens" in err.lower()


def test_missing_path_exits_nonzero(monkeypatch, tmp_path):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, [str(tmp_path / "nope"), "-o", str(tmp_path / "x")])
    assert exc.value.code == 1


def test_argv_reaches_extractor(monkeypatch, sample):
    """Smoke: CLI flags are wired through to Extractor."""
    out = sample / "cli_out.txt"
    run_main(monkeypatch, [str(sample / "app.py"), "-o", str(out), "-t", "WARN", "-i"])
    text = out.read_text(encoding="utf-8")
    assert "WARN" in text
    assert "TODO: main" not in text
