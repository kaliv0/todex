import os
import pydoc
import sys
from io import StringIO
from pathlib import Path
from typing import TextIO


class StopExtractionError(Exception):
    pass


class Writer:
    def __init__(self, path: Path | None, to_stdout=False) -> None:
        self.path = path
        self.to_stdout = to_stdout
        self.file: TextIO | None = None  # file is set on first write
        self.stdout_writer = PagedStream() if self.to_stdout and sys.stdout.isatty() else sys.stdout

    def write_header(self, path: str) -> None:
        self._write(f"======================\n{path}\n")

    def write_entry(self, lines_count: int, line: str) -> None:
        self._write(f"\tline {lines_count}: {line}")

    def debug(self, text) -> None:
        self.stdout_writer.write(text)

    def error(self, text) -> None:
        # well, it's either extract this and tell the typechecker to f*ck off or...
        if isinstance(self.stdout_writer, PagedStream):
            self.stdout_writer.write(text)
        else:
            sys.stderr.write(text)

    def _write(self, text: str) -> None:
        if self.to_stdout:
            try:
                self.stdout_writer.write(text)
                if not isinstance(self.stdout_writer, PagedStream):
                    self.stdout_writer.flush()
            except BrokenPipeError:
                self.to_stdout = False
                self.stdout_writer = sys.stdout
                if self.path is None:
                    raise StopExtractionError

        if self.path:
            if self.file is None:
                self.file = self.path.open("w", encoding="utf-8")
            self.file.write(text)
            self.file.flush()

    def close(self) -> None:
        if isinstance(self.stdout_writer, PagedStream):
            self.stdout_writer.page()

        if self.file:
            self.file.close()
            self.file = None  # for just in case


class PagedStream:
    def __init__(self) -> None:
        self._buffer = StringIO()

    def write(self, data: str) -> int:
        return self._buffer.write(data)

    def page(self) -> None:
        # set less when actually calling the pager
        if "LESS" not in os.environ:
            os.environ["LESS"] = "-RF"

        pydoc.pager(self._buffer.getvalue())
