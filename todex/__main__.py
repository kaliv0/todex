import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter

from todex.extractor import DEFAULT_MAX_DEPTH, DEFAULT_OUT, Extractor

__version__ = "1.0.0"

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
    def _format_usage(self, usage, actions, groups, prefix):
        return ""


class ArgValidator:
    def __init__(self, parser: ArgumentParser, args: Namespace) -> None:
        self.parser = parser
        self.args = args

    def require(self, flag_attr: str, needs_attr: str, flag: str, needs: str) -> None:
        if getattr(self.args, flag_attr) and not getattr(self.args, needs_attr):
            self.parser.error(f"{flag} requires {needs}")


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
        "-t",
        "--tokens",
        nargs="*",
        default=[],
        metavar="TOKEN",
        help="""list of tokens to search for (together with default TODO, FIXME) e.g. WARN, REVISIT.
If the token is followed by {lines-count} e.g. #FIXME{3}
the extractor will include multiline snippet with the length specified between the curly braces:

    #FIXME{3} - revist after release
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
        "-f", "--full-path", action="store_true", help="display absolute dir/file path"
    )
    parser.add_argument(
        "-s",
        "--short",
        action="store_true",
        help="display only token messages e.g. '#TODO:  after release', ignore longer snippets",
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
        type=int,
        metavar="N",
        default=DEFAULT_MAX_DEPTH,
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
        default=DEFAULT_OUT,
        help="path to output file, if existing dir is passed instead - TODO out file will be saved inside",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    validator = ArgValidator(parser, args)
    validator.require("ignore_default", "tokens", "-i/--ignore-default", "-t/--tokens")
    try:
        Extractor(**vars(args)).run()
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, TypeError, ValueError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
