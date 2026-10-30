import pydoc
import sys
from io import StringIO
from pathlib import Path
from typing import TextIO


class StopExtractionError(Exception):
    pass


class PagedStream:
    def __init__(self) -> None:
        self._buffer = StringIO()

    def write(self, data: str) -> int:
        return self._buffer.write(data)

    def page(self) -> None:
        pydoc.pager(self._buffer.getvalue())


class Writer:
    def __init__(self, path: Path | None, to_stdout=False) -> None:
        self.path = path
        self.to_stdout = to_stdout
        self.file = self._prepare_file()
        self.stdout_writer = self._prepare_stdout_writer()

    def _prepare_file(self) -> TextIO | None:
        if self.path:
            # we open file early - even if no tokens were found,
            # out file is left truncated with no potentially stale data
            # -> other option would be to open lazily on first write attempt
            return self.path.open("w", encoding="utf-8")
        return None

    def _prepare_stdout_writer(self) -> PagedStream | TextIO:
        if self.to_stdout and sys.stdout.isatty():
            return PagedStream()
        return sys.stdout

    def write_header(self, path: str) -> None:
        self._write(f"======================\n{path}\n")

    def write_entry(self, lines_count: int, line: str) -> None:
        self._write(f"\tline {lines_count}: {line}")

    def debug(self, text) -> None:
        self._write(text)

    def error(self, text) -> None:
        if self._is_paged_stream:
            self.stdout_writer.write(text)
        else:
            sys.stderr.write(text)

    def _write(self, text: str) -> None:
        if self.to_stdout:
            try:
                self.stdout_writer.write(text)
                if not self._is_paged_stream:
                    self.stdout_writer.flush()  # type:ignore
            except BrokenPipeError:
                self.to_stdout = False
                if self._is_paged_stream:
                    # drop pager so close() won't page() a partial buffer
                    self.stdout_writer = sys.stdout

                if self.path is None:
                    raise StopExtractionError

        if self.file is not None:
            self.file.write(text)
            self.file.flush()

    def close(self) -> None:
        if self._is_paged_stream:
            self.stdout_writer.page()  # type:ignore

        if self.file:
            self.file.close()
            self.file = None  # for just in case

    @property
    def _is_paged_stream(self) -> bool:
        return isinstance(self.stdout_writer, PagedStream)
