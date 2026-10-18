import sys

import pytest

from todex.__main__ import main


def run_main(monkeypatch, argv: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["todex", *argv])
    # main() finally closes stdout -> don't kill pytest capture
    monkeypatch.setattr(sys.stdout, "close", lambda: None)
    main()


@pytest.mark.parametrize(
    "arg, name, needs",
    [("-i", "-i/--ignore-default", "-t/--tokens"), ("-m20", "-m/--max-depth", "-r/--recursive")],
)
def test_missing_dependent_flag_errors(monkeypatch, tmp_path, capsys, arg, name, needs):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, [arg, str(tmp_path)])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err == f"todex: error: {name} flag requires {needs}\n"


@pytest.mark.parametrize(
    "extra",
    [["-s", "-o", "x"], ["-s", "--tee"]],
)
def test_stdout_mix_errors(monkeypatch, tmp_path, capsys, extra):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, [str(tmp_path), *extra])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err == "todex: error: shouldn't mix --stdout and --out or --tee flags\n"


@pytest.mark.parametrize(
    "value, message",
    [
        ("0", "expected positive value"),
        ("-1", "expected positive value"),
        ("xyz", "expected int type"),
    ],
)
def test_max_depth_rejects_invalid_values(monkeypatch, tmp_path, capsys, value, message):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, ["-r", "-m", value, str(tmp_path)])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err == f"todex: error: argument -m/--max-depth: {message}\n"


def test_missing_path_exits_nonzero(monkeypatch, tmp_path):
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, [str(tmp_path / "nope"), "-o", str(tmp_path / "x")])
    assert exc.value.code == 1


def test_argv_reaches_extractor(monkeypatch, sample):
    # NB: CLI flags are wired through to Extractor
    out = sample / "cli_out.txt"
    run_main(monkeypatch, [str(sample / "app.py"), "-o", str(out), "-t", "WARN", "-i"])
    text = out.read_text(encoding="utf-8")
    assert "WARN" in text
    assert "TODO: main" not in text


def test_r_m_limits_depth_via_cli(monkeypatch, sample):
    out = sample / "cli_depth_out.txt"
    run_main(monkeypatch, [str(sample), "-o", str(out), "-r", "-m", "1"])
    text = out.read_text(encoding="utf-8")
    assert "TODO: deep" in text
    assert "TODO: deeper" not in text


def test_s_via_cli(monkeypatch, sample, capsys, app_out):
    run_main(monkeypatch, [str(sample / "app.py"), "-s"])
    assert capsys.readouterr().out == app_out


def test_tee_via_cli(monkeypatch, sample, capsys, app_out):
    out = sample / "cli_tee_out.txt"
    run_main(monkeypatch, [str(sample / "app.py"), "-o", str(out), "--tee"])
    assert out.read_text(encoding="utf-8") == app_out
    assert capsys.readouterr().out == app_out


def test_s_broken_pipe_via_debug_exits_141(monkeypatch, sample):
    # -d writes stdout outside Writer -> BrokenPipeError reaches main
    def boom(_text: str) -> int:
        raise BrokenPipeError

    monkeypatch.setattr(sys.stdout, "write", boom)
    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, [str(sample / "app.py"), "-s", "-d"])
    assert exc.value.code == 141
