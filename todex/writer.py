import sys
from pathlib import Path
from typing import TextIO


class StopExtractError(Exception):
    pass


class Writer:
    def __init__(self, path: Path | None, to_stdout=False) -> None:
        self.path = path
        self.to_stdout = to_stdout
        self.file: TextIO | None = None

    def write_header(self, path: str) -> None:
        self._write(f"======================\n{path}\n")

    def write_entry(self, lines_count: int, line: str) -> None:
        self._write(f"\tline {lines_count}: {line}")

    def _write(self, text: str) -> None:
        if self.to_stdout:
            try:
                sys.stdout.write(text)
                sys.stdout.flush()
            except BrokenPipeError:
                self.to_stdout = False
                if self.path is None:
                    raise StopExtractError

        if self.path:
            f = self._ensure_open()
            f.write(text)
            f.flush()

    def _ensure_open(self) -> TextIO:
        if self.file is None:
            assert self.path is not None  # we shouldn't be here just to make mypy happy
            self.file = self.path.open("w", encoding="utf-8")
        return self.file

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None  # for just in case
