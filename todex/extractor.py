import re
import sys
from functools import cached_property
from pathlib import Path
from re import Pattern
from textwrap import dedent, indent

from pathspec import PathSpec

from todex.writer import StopExtractError, Writer

DEFAULT_MAX_DEPTH = 120
DEFAULT_OUT = "TODO"
DEFAULT_GLOBS = [".*", "__*"]
DEFAULT_TOKENS = ["TODO", "FIXME"]


class Extractor:
    def __init__(
        self,
        path,
        tokens: list[str] | None = None,
        ignore_default: bool = False,
        exclude: list[str] | None = None,
        include_hidden: bool = False,
        use_gitignore: bool = False,
        stdout: bool = False,
        tee: bool = False,
        out: str | None = None,
        full_path: bool = False,
        concise: bool = False,
        recursive: bool = False,
        max_depth: int | None = None,
        debug: bool = False,
    ) -> None:
        self.root = Path(path)
        self.token_pattern = self.prepare_token_pattern(tokens or [], ignore_default)
        self.exclude_spec = self.prepare_exclude_spec(exclude or [], include_hidden, use_gitignore)

        self.stdout = stdout
        self.tee = tee
        self.out = self.prepare_out_writer(out or DEFAULT_OUT)

        self.full_path = full_path
        self.concise = concise

        self.recursive = recursive
        # the CLI sets max_depth to None if omitted so we need to set the default explicitly
        self.max_depth = DEFAULT_MAX_DEPTH if max_depth is None else max_depth

        self.debug = __debug__ and debug

    @staticmethod
    def prepare_token_pattern(tokens: list[str], ignore_default: bool) -> Pattern:
        if not ignore_default:
            tokens = [*DEFAULT_TOKENS, *tokens]

        if not tokens:
            # prevented by CLI (-i without -t) but you can never be too careful
            raise ValueError("no tokens to search for")

        tokens = sorted(dict.fromkeys(tokens), key=len, reverse=True)
        alternations = "|".join(re.escape(tok) for tok in tokens)
        return re.compile(rf"(?<!\w)(?:{alternations})(?!\w)", re.IGNORECASE)

    def prepare_exclude_spec(self, exclude: list[str], include_hidden: bool, use_gitignore: bool) -> PathSpec:
        if use_gitignore and self.root.is_dir():
            exclude = [*self.get_gitignore_patterns(), *exclude]

        if not include_hidden:
            exclude = [*DEFAULT_GLOBS, *exclude]

        exclude = list(dict.fromkeys(exclude))  # dedupe + keep order
        # NB: ignores blank/# lines from .gitignore file
        return PathSpec.from_lines("gitignore", exclude)

    def get_gitignore_patterns(self) -> list[str]:
        if (gitignore_file := self.root / ".gitignore").is_file():
            return gitignore_file.read_text(encoding="utf-8").splitlines()
        return []

    def prepare_out_writer(self, name: str) -> Writer:
        if self.stdout:
            return Writer(path=None, to_stdout=True)

        if (path := Path(name)).is_dir():
            path = path / DEFAULT_OUT
        return Writer(path, to_stdout=bool(self.tee))

    @cached_property
    def out_path(self) -> Path | None:
        if self.out.path is None:
            return None
        return self.out.path.absolute()

    def run(self) -> None:
        if not self.root.exists():
            raise FileNotFoundError(f"{self.root} not found")

        if self.debug:
            # it could be simple print() but don't want to mix both out of superstition
            sys.stdout.write("processing:\n")
        try:
            if self.root.is_file():
                self.process_file(self.root)
            elif self.root.is_dir():
                self.process_dir(self.root, depth=0)
            else:
                raise ValueError(f"{self.root} must be path to file or dir")
        except StopExtractError:
            # e.g. tdx . -s | head 5 -> stop early after 'head' exits
            pass
        finally:
            self.out.close()

    def process_file(self, path: Path) -> None:
        if self.is_excluded(path):
            return

        if self.debug:
            sys.stdout.write(f"\t{self.prepare_path_name(path)}\n")

        try:
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

                    if self.concise:
                        line = line[idx:]
                        self.out.write_entry(lines_count, line)
                        continue

                    display_line_num = lines_count
                    for _ in range(
                        1,
                        self.get_snippet_count(line, start=idx + len(token), line_num=display_line_num),
                    ):
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
        except UnicodeDecodeError as e:
            if self.debug:
                sys.stderr.write(f"skipping {self.prepare_path_name(path)}:\n{e}\n")

    def get_snippet_count(self, line: str, start: int, line_num: int) -> int:
        if not line.startswith("{", start):
            return 1

        # advance pointer to actual count
        start = start + 1
        if (end := line[start:].find("}")) == -1:
            err = ValueError("invalid snippet count")
            self._add_debug_note(err, line, line_num)
            raise err

        try:
            snippet_count = int(line[start : start + end])
        except ValueError as err:
            self._add_debug_note(err, line, line_num)
            raise
        return snippet_count

    def _add_debug_note(self, err: Exception, line: str, line_num: int) -> None:
        if self.debug:
            err.add_note(f"\tline {line_num}: {line.strip()}")

    def prepare_path_name(self, path: Path) -> str:
        if self.full_path:
            return str(path.absolute())
        if self.recursive:
            return str(path)
        return path.name

    def process_dir(self, path: Path, depth: int) -> None:
        if self.is_excluded(path, is_dir=True) or depth > self.max_depth:
            return

        dirs = []
        for entry in path.iterdir():
            if entry.is_file():
                self.process_file(entry)
            elif self.recursive and entry.is_dir():
                dirs.append(entry)

        for dir_ in dirs:
            self.process_dir(dir_, depth + 1)

    def is_excluded(self, path: Path, is_dir: bool = False) -> bool:
        # always process scan root
        if path == self.root:
            return False

        # skip summary file
        if path.absolute() == self.out_path:
            return True

        rel_path = path.relative_to(self.root).as_posix()
        if is_dir:
            return any(self.exclude_spec.match_files([rel_path, rel_path + "/"]))
        return self.exclude_spec.match_file(rel_path)
