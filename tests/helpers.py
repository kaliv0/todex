import sys


def broken_pipe_write(_text: str = "") -> int:
    raise BrokenPipeError


class BrokenFlushOnce:
    # one-shot: pytest teardown may flush stdout again after the test
    def __init__(self) -> None:
        self.broken = True

    def __call__(self) -> None:
        if self.broken:
            self.broken = False
            raise BrokenPipeError


def patch_stdout_broken_flush(monkeypatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "write", lambda _text: 1)
    monkeypatch.setattr(sys.stdout, "flush", BrokenFlushOnce())


def write_good_and_bad(tmp_path) -> None:
    (tmp_path / "good.py").write_text("# TODO: keep me\n", encoding="utf-8")
    (tmp_path / "bad.bin").write_bytes(b"\xff\xfe TODO: binary\n")
