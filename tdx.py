#! /usr/bin/python3


from pathlib import Path
from textwrap import dedent, indent


class Writer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.opened = False
        self.file = None

    def open(self):
        if not self.opened:
            self.file = self.path.open("w")
            self.opened = True

    def close(self):
        if self.opened and self.file:  # fixme
            self.file.close()
            self.opened = False

    def write(self, line: str):
        if self.file:  # fixme
            self.file.write(line)


class Processor:
    def __init__(
        self,
        exclude=None,
        tokens=None,
        full_path=False, # default values can be set in arg_parser before this step
        short=True,
        recursive=True,
        max_depth=float("inf"),
        out="TODO.txt",
    ) -> None:  # fix default max_depth and out
        self.exclude = exclude or {".idea", ".venv", ".zed"}  # fixme
        self.tokens = tokens or {}
        self.full_path = full_path
        self.short = short
        self.recursive = recursive
        self.max_depth = max_depth
        self.out = self.prepare_out(out)

    @staticmethod
    def prepare_out(name) -> Writer:
        path = Path(name)  # actually from args
        if not path.exists:
            raise FileNotFoundError("path not found")

        if path.is_dir():
            raise TypeError("out path must file not dir")
        return Writer(path)

    def run(self):
        path = Path(".")  # actually from args
        if not path.exists:
            raise FileNotFoundError("path not found")

        try:
            if path.is_file():
                self.process_file(path)
                # exit(0)

            if path.is_dir():
                self.process_dir(path, depth=0)
        # except (Exception, KeyboardInterrupt) as e:
        #     print(e)
        finally:
            if not self.out.opened:
                self.out.close()

    def process_file(self, path: Path):
        if path in self.exclude or path.name.startswith("TODO"):  # check for globs
            return

        with path.open() as f:
            i = 0  # lines count
            header_added = False
            while line := f.readline():
                i += 1
                # //if line not contains "TODO", "FIXME" or --tokens:
                if (idx := line.find("TODO")) == -1:
                    continue

                # // NB: we also need to know which token was found -> we use it's size inside parse_snippet_count()

                # lazy open out file
                if not self.out.opened:
                    self.out.open()

                if not header_added:
                    self.out.write("======================\n")
                    self.out.write(f"{self.prepare_path_name(path)}\n")
                    header_added = True

                line_num = i
                if self.short:
                    line = line[idx:]
                else:
                    for _ in range(1, self.get_snippet_count(line, idx)):
                        line += f.readline()
                        i += 1

                    if not line.endswith("\n"):
                        # if this is the last line of the file
                        line += "\n"

                    if line_num != i:
                        # prepare snippet
                        line = indent(dedent("\n" + line), "\t\t")
                    else:
                        line = dedent(line)

                self.out.write(f"\tline {line_num}: ")
                self.out.write(line)

    @staticmethod
    def get_snippet_count(line: str, idx: int) -> int:
        start = idx + len("TODO")
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
            return str(path.resolve())  # NB: use for symlinks
        if self.recursive:
            return str(path)
        return path.name

    def process_dir(self, path: Path, depth: int):
        if path.name in self.exclude or path.name.startswith(
            (".", "_")
        ):  # check for globs
            return

        if depth > self.max_depth:
            return

        for entry in path.iterdir():  # handle error? (OSError)
            if entry.is_file():
                self.process_file(entry)

            elif self.recursive and entry.is_dir():
                self.process_dir(entry, depth + 1)


def main():
    # resolve args
    args = []
    Processor(*args).run()


if __name__ == "__main__":
    main()
