from pathlib import Path
from typing import TextIO


class Writer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.file: TextIO | None = None

    def ensure_open(self) -> TextIO:
        if self.file is None:
            self.file = self.path.open("w")
        return self.file

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None

    def write_header(self, path: str) -> None:
        f = self.ensure_open()
        f.write("======================\n")
        f.write(f"{path}\n")

    def write_entry(self, lines_count: int, line: str) -> None:
        f = self.ensure_open()
        f.write(f"\tline {lines_count}: ")
        f.write(line)
