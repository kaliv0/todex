#! /usr/bin/python3


import re
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from fnmatch import fnmatch
from pathlib import Path
from re import Pattern
from textwrap import dedent, indent
from typing import TextIO

__version__ = "1.0.0"

DEFAULT_MAX_DEPTH = float("inf")
DEFAULT_OUT = "TODO"
DEFAULT_TOKENS = ["TODO", "FIXME"]

TRASH = r"""
       ________________   ___/-\___     ___/-\___     ___/-\___
     / /             ||  |---------|   |---------|   |---------|
    / /              ||   |       |     | | | | |     |   |   |
   / /             __||   |       |     | | | | |     | | | | |
  / /   \\        I  ||   |       |     | | | | |     | | | | |
 (-------------------||   | | | | |     | | | | |     | | | | |
 ||               == ||   |_______|     |_______|     |_______|
 ||       TODEX      | =============================================
 ||          ____    |                                ____      |
( | o      / ____ \                                 / ____ \    |)
 ||      / / . . \ \                              / / . . \ \   |
[ |_____| | .   . | |____________________________| | .   . | |__]
          | .   . |                                | .   . |
           \_____/                                  \_____/

            Peak trash sniffer and TODO extractor
"""


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

    def write_entry(self, lines_count: int, line: str) -> None:
        self.ensure_open()
        self.file.write(f"\tline {lines_count}: ")
        self.file.write(line)


class Extractor:
    def __init__(
        self,
        path,
        exclude: list[str] | None = None,
        glob: bool = False,
        tokens: list[str] | None = None,
        ignore_default: bool = False,
        full_path: bool = False,
        short: bool = False,
        recursive: bool = False,
        max_depth: float = DEFAULT_MAX_DEPTH,
        out: str = DEFAULT_OUT,
    ) -> None:
        self.root = Path(path)

        self.exclude = set(exclude or [])
        self.use_glob = glob

        self.token_pattern = self.prepare_token_pattern(tokens or [], ignore_default)

        self.full_path = full_path
        self.short = short
        self.recursive = recursive
        self.max_depth = max_depth

        self.out = self.prepare_out(out)
        self.out_path = self.out.path.absolute()

    @staticmethod
    def prepare_token_pattern(tokens: list[str], ignore_default: bool) -> Pattern:
        if not (ignore_default and tokens):
            tokens = [*DEFAULT_TOKENS, *tokens]
        tokens = sorted(set(tokens), key=len, reverse=True)
        return re.compile(
            rf"(?<!\w)(?:{'|'.join(re.escape(tok) for tok in tokens)})(?!\w)", re.IGNORECASE
        )

    @staticmethod
    def prepare_out(name: str) -> Writer:
        if (path := Path(name)).is_dir():
            raise TypeError("out path must file not dir")
        return Writer(path)

    def run(self) -> None:
        if not self.root.exists():
            raise FileNotFoundError(f"{self.root} not found")

        try:
            if self.root.is_file():
                self.process_file(self.root)
            elif self.root.is_dir():
                self.process_dir(self.root, depth=0)
            else:
                print(f"{self.root} must be path to file or dir")
        # OSError might be raised from path.iterdir, also catches FileNotFoundError
        except (OSError, ValueError, TypeError, RuntimeError) as e:  # revisit
            print(e)
        except KeyboardInterrupt:
            pass
        finally:
            self.out.close()

    def process_file(self, path: Path) -> None:
        if self.is_excluded(path):
            return

        with path.open() as f:
            lines_count = 0
            header_added = False
            while line := f.readline():
                lines_count += 1

                if not (match := self.token_pattern.search(line)):
                    continue
                token = match.group()
                idx = match.start()

                if not header_added:
                    self.out.write_header(self.prepare_path_name(path))
                    header_added = True

                if self.short:
                    line = line[idx:]
                    self.out.write_entry(lines_count, line)
                    continue

                display_line_num = lines_count
                for _ in range(1, self.get_snippet_count(line, start=idx + len(token))):
                    if not (next_line := f.readline()):
                        break
                    line += next_line
                    lines_count += 1

                if not line.endswith("\n"):
                    line += "\n"  # this is the last or only line in the file

                if display_line_num != lines_count:  # add full snippets
                    line = indent(dedent("\n" + line), "\t\t")
                else:
                    line = dedent(line)
                self.out.write_entry(display_line_num, line)

    @staticmethod
    def get_snippet_count(line: str, start: int) -> int:
        if not line.startswith("{", start):
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
        if self.is_excluded(path):
            return

        if depth > self.max_depth:
            return

        dirs = []
        for entry in path.iterdir():
            if entry.is_file():
                self.process_file(entry)
            elif self.recursive and entry.is_dir():
                dirs.append(entry)

        for dir_ in dirs:
            self.process_dir(dir_, depth + 1)

    def is_excluded(self, path: Path) -> bool:
        # skip summary file
        if path.absolute() == self.out_path:
            return True

        # always process scan root
        if path == self.root:
            return False

        rel_path = path.relative_to(self.root).as_posix()
        name = path.name
        if self.use_glob:
            return any(fnmatch(rel_path, entry) or fnmatch(name, entry) for entry in self.exclude)
        # exact path under root or name anywhere in nested dirs under root
        return rel_path in self.exclude or name in self.exclude


class NoUsageFormatter(RawDescriptionHelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        return ""

def main() -> None:
    parser = ArgumentParser(
        prog="todex",
        formatter_class=NoUsageFormatter,
        description=TRASH,
    )
    parser.add_argument("path", metavar="PATH", help="path to file or dir to process")
    parser.add_argument(
        "-x",
        "--exclude",
        nargs="*",
        default=[],
        help="list of dirs/files to exclude - accepts glob pattern combined with -g/--glob flag",
    )
    parser.add_argument(
        "-g",
        "--glob",
        action="store_true",
        help="exclude entries matching -x glob patterns",
    )
    parser.add_argument(
        "-t",
        "--tokens",
        nargs="*",
        default=[],
        help="list of tokens to search for (together with default TODO, FIXME) e.g. WARN, REVISIT",
    )
    parser.add_argument(
        "-i",
        "--ignore-default",
        action="store_true",
        help="use only -t tokens (skip default TODO, FIXME)",
    )
    parser.add_argument(
        "-f", "--full-path", action="store_true", help="display absolute dir/file path"
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
        "--max-depth",
        type=int,
        metavar="N",
        default=DEFAULT_MAX_DEPTH,
        help="maximum depth of dir traversal - used with --recursive flag",
    )
    parser.add_argument("-o", "--out", default=DEFAULT_OUT, help="path to output file")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()
    Extractor(**vars(args)).run()


if __name__ == "__main__":
    main()
