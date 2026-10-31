import re
from functools import cached_property
from pathlib import Path
from re import Pattern
from textwrap import dedent, indent
from typing import TextIO

from pathspec import PathSpec

from todex.writer import Writer

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
        self.root = self._prepare_root(path)
        self.token_pattern = self._prepare_token_pattern(tokens or [], ignore_default)
        self.exclude_spec = self._prepare_exclude_spec(exclude or [], include_hidden, use_gitignore)

        self.out = self._prepare_out_writer(out or DEFAULT_OUT, stdout, tee)

        self.full_path = full_path
        self.concise = concise

        self.recursive = recursive
        # the CLI sets max_depth to None if omitted so we need to set the default explicitly
        self.max_depth = self._prepare_max_depth(max_depth)

        self.debug = __debug__ and debug

    @staticmethod
    def _prepare_root(path: str) -> Path:
        if not (root := Path(path)).exists():
            raise FileNotFoundError(f"{root} not found")
        return root

    @staticmethod
    def _prepare_token_pattern(tokens: list[str], ignore_default: bool) -> Pattern:
        if not ignore_default:
            tokens = [*DEFAULT_TOKENS, *tokens]

        if not tokens:
            # prevented by CLI (-i without -t) but you can never be too careful
            raise ValueError("no tokens to search for")

        tokens = sorted(dict.fromkeys(tokens), key=len, reverse=True)
        alternations = "|".join(re.escape(tok) for tok in tokens)
        return re.compile(rf"(?<!\w)(?:{alternations})(?!\w)", re.IGNORECASE)

    def _prepare_exclude_spec(
        self, exclude: list[str], include_hidden: bool, use_gitignore: bool
    ) -> PathSpec:
        if use_gitignore and self.root.is_dir():
            exclude = [*self._get_gitignore_patterns(), *exclude]

        if not include_hidden:
            exclude = [*DEFAULT_GLOBS, *exclude]

        exclude = list(dict.fromkeys(exclude))  # dedupe + keep order
        # NB: ignores blank/# lines from .gitignore file
        return PathSpec.from_lines("gitignore", exclude)

    def _get_gitignore_patterns(self) -> list[str]:
        if (gitignore_file := self.root / ".gitignore").is_file():
            return gitignore_file.read_text(encoding="utf-8").splitlines()
        return []

    def _prepare_out_writer(self, name: str, stdout: bool, tee: bool) -> Writer:
        if stdout:
            return Writer(path=None, to_stdout=True)

        if (path := Path(name)).is_dir():
            path = path / DEFAULT_OUT
        return Writer(path, to_stdout=tee)

    @staticmethod
    def _prepare_max_depth(max_depth: int | None) -> int:
        if max_depth is None:
            return DEFAULT_MAX_DEPTH
        if max_depth <= 0:
            raise ValueError("max_depth must be a positive integer")
        return max_depth

    @cached_property
    def out_path(self) -> Path | None:
        return self.out.path and self.out.path.absolute()

    def run(self) -> None:
        try:
            if self.debug:
                # it could be simple print() but don't want to mix both out of superstition
                self.out.debug("processing:\n")

            if self.root.is_file():
                self.process_file(self.root)
            elif self.root.is_dir():
                self.process_dir(self.root, depth=0)
            else:
                raise ValueError(f"{self.root} must be path to file or dir")
        # tdx . -s | head 5 -> let StopExtractionError propagate automatically
        finally:
            self.out.close()

    def process_file(self, path: Path) -> None:
        if self._is_excluded(path):
            return

        if self.debug:
            self.out.debug(f"\t{self._prepare_path_name(path)}\n")
        try:
            with path.open(encoding="utf-8") as f:
                lines_count = 0
                header_added = False
                while line := f.readline():
                    lines_count += 1
                    if not (match := self.token_pattern.search(line)):
                        continue
                    lines_count, header_added = self._write_hit(
                        f, path, line, lines_count, match, header_added
                    )
        except UnicodeDecodeError as e:
            if self.debug:
                self.out.error(f"skipping {self._prepare_path_name(path)}:\n{e}\n")

    def _write_hit(
        self,
        source: TextIO,
        path: Path,
        line: str,
        lines_count: int,
        match: re.Match[str],
        header_added: bool,
    ) -> tuple[int, bool]:
        if not header_added:
            self.out.write_header(self._prepare_path_name(path))
            header_added = True

        snippet_count = self._get_snippet_count_after_token(line, token_end=match.end(), line_num=lines_count)
        if self.concise:
            self.out.write_entry(lines_count, line[match.start() :])
            return lines_count, header_added

        display_line_num = lines_count
        for _ in range(1, snippet_count):
            if not (next_line := source.readline()):
                break
            line += next_line
            lines_count += 1

        self.out.write_entry(
            display_line_num,
            self._format_snippet_entry(line, multi=display_line_num != lines_count),
        )
        return lines_count, header_added

    @staticmethod
    def _format_snippet_entry(line: str, multi: bool) -> str:
        if not line.endswith("\n"):
            line += "\n"  # this is the last or only line in the file
        if multi:
            return indent(dedent("\n" + line), "\t\t")
        return dedent(line)

    def _get_snippet_count_after_token(self, line: str, token_end: int, line_num: int) -> int:
        if not line.startswith("{", token_end):
            return 1

        # advance pointer to actual count
        start = token_end + 1
        if (end := line[start:].find("}")) == -1:
            err = ValueError("invalid snippet count: unclosed '{'")
            self._add_debug_note(err, line, line_num)
            raise err

        body = line[start : start + end]
        try:
            return int(body)
        except ValueError:
            err = ValueError(f"invalid snippet count: {body!r}")
            self._add_debug_note(err, line, line_num)
            raise err

    def _add_debug_note(self, err: Exception, line: str, line_num: int) -> None:
        if self.debug:
            err.add_note(f"\tline {line_num}: {line.strip()}")

    def _prepare_path_name(self, path: Path) -> str:
        if self.full_path:
            return str(path.absolute())
        if self.recursive:
            return str(path)
        return path.name

    def process_dir(self, path: Path, depth: int) -> None:
        if self._is_excluded(path, is_dir=True) or depth > self.max_depth:
            return

        opts = {"follow_symlinks": False}
        dirs = []
        for entry in sorted(path.iterdir(), key=lambda x: x.name):
            if entry.is_file(**opts):
                self.process_file(entry)
            elif self.recursive and entry.is_dir(**opts):
                dirs.append(entry)

        for dir_ in dirs:
            self.process_dir(dir_, depth + 1)

    def _is_excluded(self, path: Path, is_dir: bool = False) -> bool:
        # always process scan root
        if path == self.root:
            return False
        # skip summary file
        if path.absolute() == self.out_path:
            return True

        rel_paths = [rel := path.relative_to(self.root).as_posix()]
        if is_dir:
            rel_paths.append(rel + "/")
        return any(self.exclude_spec.match_files(rel_paths))
