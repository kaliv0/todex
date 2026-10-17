import sys
import traceback
from argparse import (
    Action,
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    RawTextHelpFormatter,
    _HelpAction,
    _MutuallyExclusiveGroup,
    _VersionAction,
)
from collections.abc import Iterable
from functools import cached_property
from typing import ClassVar

from todex import __version__
from todex.extractor import Extractor

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


class NoUsageFormatter(RawTextHelpFormatter):
    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[Action],
        groups: Iterable[_MutuallyExclusiveGroup],
        prefix: str | None,
    ) -> str:
        return ""


class ArgValidator:
    DEPENDENT_FLAGS: ClassVar[dict[str, str]] = {
        "ignore_default": "tokens",
        "max_depth": "recursive",
    }

    def __init__(self, parser: ArgumentParser, args: Namespace) -> None:
        self.parser = parser
        self.args = args

    @cached_property
    def attrs_to_flags(self) -> dict[str, str]:
        return {
            action.dest: "/".join(action.option_strings)
            for action in self.parser._actions
            if not isinstance(action, (_HelpAction, _VersionAction)) and action.option_strings
        }

    def validate(self) -> None:
        self._validate_dependent_flags()
        self._validate_output_streams()

    def _validate_dependent_flags(self) -> None:
        for name, needs in self.DEPENDENT_FLAGS.items():
            if getattr(self.args, name) and not getattr(self.args, needs):
                self.parser.error(f"{self.attrs_to_flags[name]} flag requires {self.attrs_to_flags[needs]}")

    def _validate_output_streams(self) -> None:
        stdout, out, tee = self.args.stdout, self.args.out, self.args.tee
        if stdout and (out or tee):
            self.parser.error("shouldn't mix --stdout and --out or --tee flags")


def require_positive_int(value: str) -> int:
    try:
        num = int(value)
    except ValueError as e:
        raise ArgumentTypeError("expected int type") from e

    if num <= 0:
        raise ArgumentTypeError("expected positive value")
    return num


def main() -> None:
    parser = ArgumentParser(
        prog=sys.argv[0],
        formatter_class=NoUsageFormatter,
        description=TRASH,
    )
    parser.add_argument("path", metavar="PATH", help="path to file or dir to process")
    parser.add_argument(
        "-t",
        "--tokens",
        nargs="+",
        metavar="TOKEN",
        help="""list of tokens to search for (together with default TODO, FIXME) e.g. WARN, REVISIT.
If the token is followed by {lines-count} e.g. #FIXME{3}
the extractor will include multiline snippet with the length specified between the curly braces:

    #FIXME{3} - revisit after release
    if self.foo == "bar":
        return f"fizz{buzz}"

""",
    )
    parser.add_argument(
        "-i",
        "--ignore-default",
        action="store_true",
        help="use only -t tokens (skip default TODO, FIXME)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        nargs="+",
        metavar="PATTERN",
        help="""git-like patterns to skip (paths, names, or globs together with default .* / __*), e.g.

    bar.py       any file named bar.py
    /bar.py      only top-level
    foo/bar.py   path under the scan root
    vendor/      directory and its contents
    **/*.pyc     nested matches
    !fizz.md     re-include after a broader exclude

""",
    )
    parser.add_argument(
        "-H",
        "--include-hidden",
        action="store_true",
        help="do not apply default excludes for hidden names (.* / __*)",
    )
    parser.add_argument(
        "-g",
        "--use-gitignore",
        action="store_true",
        help="use exclude patterns from .gitignore (if present in scan root) when traversing dirs",
    )
    parser.add_argument("-f", "--full-path", action="store_true", help="display absolute dir/file path")
    parser.add_argument(
        "-c",
        "--concise",
        action="store_true",
        help="display only token messages e.g. '#TODO{5}: after release', ignore longer snippets",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="traverse given dir path recursively",
    )
    parser.add_argument(
        "-m",
        "--max-depth",
        type=require_positive_int,
        metavar="N",
        help="maximum depth of dir traversal - used with -r/--recursive flag",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="enable debug mode",
    )
    parser.add_argument(
        "-o",
        "--out",
        help="path to output file - if existing dir is passed instead TODO out file will be saved inside the path",
    )
    parser.add_argument("-s", "--stdout", action="store_true", help="output result to stdout")
    parser.add_argument("--tee", action="store_true", help="output result to stdout and save to file")
    parser.add_argument("-v", "--version", action="version", version=__version__)

    args = parser.parse_args()
    ArgValidator(parser, args).validate()

    try:
        Extractor(**vars(args)).run()
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, TypeError, ValueError) as e:
        traceback.print_exception(e, limit=0, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
