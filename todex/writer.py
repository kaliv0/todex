import sys
from pathlib import Path
from typing import TextIO


class Writer:
    def __init__(self, path: Path | None, to_stdout=False) -> None:
        self.path = path
        self.to_stdout = to_stdout
        self.file: TextIO | None = None
        self._streams: list[TextIO] = []

    @property
    def streams(self) -> list[TextIO]:
        if not self._streams:
            if self.to_stdout:
                self._streams.append(sys.stdout)

            if self.path:
                # buffering=1 forces line-buffering so logs sync immediately
                self.file = self.path.open("w", encoding="utf-8", buffering=1)
                self._streams.append(self.file)
        return self._streams

    def write_header(self, path: str) -> None:
        for f in self.streams:
            f.write(f"======================\n{path}\n")

    def write_entry(self, lines_count: int, line: str) -> None:
        for f in self.streams:
            f.write(f"\tline {lines_count}: {line}")

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None
        self._streams.clear()
