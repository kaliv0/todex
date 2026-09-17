#! /usr/bin/python3


import re
from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent, indent
from typing import TextIO

DEFAULT_MAX_DEPTH = float("inf")
DEFAULT_OUT = "TODO"


class Writer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.file: TextIO | None = None

    def ensure_open(self) -> None:
        # lazy open out file
        if self.file is None:
            self.file = self.path.open("w")

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None

    def write_header(self, path: str) -> None:
        self.ensure_open()
        self.file.write("======================\n")
        self.file.write(f"{path}\n")

    def write_entry(self, line: str) -> None:
        self.ensure_open()
        self.file.write(line)


class Extractor:
    def __init__(
        self,
        path,
        exclude: list[str] | None = None,
        tokens: list[str] | None = None,
        full_path: bool = False,
        short: bool = False,
        recursive: bool = False,
        max_depth: float = DEFAULT_MAX_DEPTH,
        out: str = DEFAULT_OUT,
    ) -> None:
        self.path = path
        self.exclude = exclude or []
        self.tokens = tokens or []
        self.full_path = full_path
        self.short = short
        self.recursive = recursive
        self.max_depth = max_depth
        self.out = self.prepare_out(out)

    @staticmethod
    def prepare_out(name: str) -> Writer:
        path = Path(name)
        if not path.exists:
            raise FileNotFoundError("path not found")

        if path.is_dir():
            raise TypeError("out path must file not dir")
        return Writer(path)

    def run(self) -> None:
        path = Path(self.path)
        if not path.exists:
            raise FileNotFoundError(f"{path} not found")

        try:
            if path.is_file():
                self.process_file(path)
            elif path.is_dir():
                self.process_dir(path, depth=0)
            else:
                print(f"{path} must be path to file or dir")
        # OSError might be raised from path.iterdir, also catches FileNotFoundError
        except (OSError, ValueError, TypeError, RuntimeError) as e:  # revisit
            print(e)
        except KeyboardInterrupt:
            pass
        finally:
            self.out.close()

    def process_file(self, path: Path) -> None:
        if path in self.exclude or path.name.startswith("TODO"):  # check for globs
            return

        with path.open() as f:
            lines_count = 0
            header_added = False
            while line := f.readline():
                lines_count += 1

                # pattern = "|".join(re.escape(tok) for tok in self.tokens # do we need to escape specail chars in tok
                pattern = rf"\b(?:{"|".join(self.tokens)})\b"
                if not (match := re.search(pattern, line, re.IGNORECASE)):
                    continue
                token = match.group()
                idx = match.start()

                if not header_added:
                    self.out.write_header(self.prepare_path_name(path))
                    header_added = True

                if self.short:
                    line = line[idx:]
                    self.out.write_entry(f"\tline {lines_count}: ")
                    self.out.write_entry(line)
                    continue

                display_line_num = lines_count
                for _ in range(1, self.get_snippet_count(line, start=idx + len(token))):
                    line += f.readline()
                    lines_count += 1

                if not line.endswith("\n"):
                    line += "\n"  # this is the last or only line in the file

                self.out.write_entry(f"\tline {display_line_num}: ")
                if display_line_num != lines_count:  # add full snippets
                    self.out.write_entry(indent(dedent("\n" + line), "\t\t"))
                else:
                    self.out.write_entry(dedent(line))

    @staticmethod
    def get_snippet_count(line: str, start: int) -> int:
        if line[start] != "{":
            return 1

        # advance pointer to actual count
        start = start + 1

        if (end := line[start:].find("}")) == -1:
            raise ValueError("invalid snippet count")
        # cut snippet line count and try parse to int -> if it fails global error handler will log the error
        return int(line[start : start + end])

    def prepare_path_name(self, path: Path) -> str:
        if self.full_path:
            return str(path.absolute())  # NB: use resolve() for symlinks
        if self.recursive:
            return str(path)
        return path.name

    def process_dir(self, path: Path, depth: int) -> None:
        if path.name in self.exclude or path.name.startswith(
            (".", "_")
        ):  # check for globs
            return

        if depth > self.max_depth:
            return

        dirs = []
        for entry in path.iterdir():
            if entry.is_file():
                self.process_file(entry)
            elif self.recursive and entry.is_dir():
                dirs.append(entry)

        if dirs:
            for dir_ in dirs:
                self.process_dir(dir_, depth + 1)


def main() -> None:
    parser = ArgumentParser()
    # add types for args, fix help msgs
    parser.add_argument("path", metavar="PATH", help="path to file or dir to process")
    parser.add_argument(
        "-x",
        "--exclude",
        nargs="*",
        default=[],
        help="list of dirs/files to exclude - also works with glob patterns",
    )
    parser.add_argument(
        "-t",
        "--tokens",
        nargs="*",
        default=[],
        help="list of tokens to search for (besides the default TODO, FIXME) e.g. WARN, REVISIT",
    )
    parser.add_argument(
        "-f", "--full_path", action="store_true", help="display absolute dir/file path"
    )
    parser.add_argument(
        "-s",
        "--short",
        action="store_true",
        help="display only tokens messages - ignores longer snippets",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="traverse given dir path recursively",
    )
    parser.add_argument(
        "-d",
        "--max_depth",
        default=DEFAULT_MAX_DEPTH,
        help="maximum depth of dir traversal - used with --recursive flag",
    )
    parser.add_argument("-o", "--out", default=DEFAULT_OUT, help="path to output file")

    args = parser.parse_args()
    Extractor(**vars(args)).run()


if __name__ == "__main__":
    main()
