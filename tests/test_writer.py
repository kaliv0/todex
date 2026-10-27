import os
import sys

import pytest

from todex.writer import PagedStream, Writer


@pytest.fixture
def tty(monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)


def test_non_tty_uses_stdout(monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    w = Writer(path=None, to_stdout=True)
    assert w.stdout_writer is sys.stdout


def test_tty_buffers_and_pages_on_close(tty, monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr("todex.writer.pydoc.pager", seen.append)

    w = Writer(path=None, to_stdout=True)
    assert isinstance(w.stdout_writer, PagedStream)

    w.write_header("a.py")
    w.write_entry(1, "# TODO: x\n")
    assert seen == []

    w.close()
    assert seen == ["======================\na.py\n\tline 1: # TODO: x\n"]


def test_tty_error_goes_to_pager_buffer(tty, monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr("todex.writer.pydoc.pager", seen.append)

    w = Writer(path=None, to_stdout=True)
    assert isinstance(w.stdout_writer, PagedStream)

    w.error("boom\n")
    w.close()
    assert seen == ["boom\n"]


def test_non_tty_error_goes_to_stderr(monkeypatch, capsys):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    w = Writer(path=None, to_stdout=True)
    w.error("boom\n")
    assert capsys.readouterr().err == "boom\n"


def test_tty_tee_pages_and_writes_file(tty, tmp_path, monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr("todex.writer.pydoc.pager", seen.append)
    out = tmp_path / "out.txt"

    w = Writer(path=out, to_stdout=True)
    w.write_entry(1, "# TODO: x\n")
    w.close()

    assert seen == ["\tline 1: # TODO: x\n"]
    assert out.read_text(encoding="utf-8") == "\tline 1: # TODO: x\n"


def test_out_path_truncated_on_init(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text("stale\n", encoding="utf-8")
    w = Writer(path=out)
    w.close()
    assert out.read_text(encoding="utf-8") == ""


def test_page_does_not_set_less_when_unset(tty, monkeypatch):
    monkeypatch.delenv("LESS", raising=False)
    monkeypatch.setattr("todex.writer.pydoc.pager", lambda _text: None)

    w = Writer(path=None, to_stdout=True)
    w.write_entry(1, "# TODO: x\n")
    w.close()
    assert "LESS" not in os.environ


def test_page_preserves_less_when_set(tty, monkeypatch):
    monkeypatch.setenv("LESS", "X")
    monkeypatch.setattr("todex.writer.pydoc.pager", lambda _text: None)

    w = Writer(path=None, to_stdout=True)
    w.write_entry(1, "# TODO: x\n")
    w.close()
    assert os.environ["LESS"] == "X"


def test_page_accepts_pager_with_args(tty, monkeypatch, tmp_path):
    log = tmp_path / "paged.txt"
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setenv("PAGER", f"tee {log}")

    w = Writer(path=None, to_stdout=True)
    w.write_entry(1, "# TODO: x\n")
    w.close()

    assert "\tline 1: # TODO: x\n" in log.read_text(encoding="utf-8")
