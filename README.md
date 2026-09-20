<div align="center">
  <img src="https://github.com/kaliv0/todex/blob/main/assets/truck.jpg?raw=true" width="400" alt="Todex">
</div>

# todex

![Python 3.X](https://img.shields.io/badge/python-^3.12-blue?style=flat-square&logo=Python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/todex.svg)](https://pypi.org/project/todex/)
[![Downloads](https://static.pepy.tech/badge/todex)](https://pepy.tech/projects/todex)

Peak mud digger and TODO extractor

```bash
pipx install todex

todex <PATH> [OPTIONS...]
```

 You can also invoke `todex` using the shorter alias `tdx`.


| Which | What |
| --- | --- |
| `PATH` | path to file or dir to process |
| `-h`, `--help` | show this help message and exit |
| `-x`, `--exclude [PATTERN ...]` | git-like patterns to skip (paths, names, or globs together with default .* / __* ), e.g.<br><br><table><tr><td>bar.py</td><td>any file named bar.py</td></tr><tr><td>/bar.py</td><td>only top-level</td></tr><tr><td>foo/bar.py</td><td>path under the scan root</td></tr><tr><td>vendor/</td><td>directory and its contents</td></tr><tr><td>**/*.pyc</td><td>nested matches</td></tr><tr><td>!fizz.md</td><td>re-include after a broader exclude</td></tr></table> |
| `-H`, `--include-hidden` | do not apply default excludes for hidden names (.* / __*) |
| `-t`, `--tokens [TOKEN ...]` | list of tokens to search for (together with default TODO, FIXME)<br>e.g. WARN, REVISIT.<br>If the token is followed by {lines-count} e.g. #FIXME{3}<br>the extractor will include multiline snippet with the length specified between the curly braces:<br><br>#FIXME{3} - revist after release<br>if self.foo == "bar":<br>&nbsp;&nbsp;&nbsp;&nbsp;return f"fizz{buzz}" |
| `-i`, `--ignore-default` | use only -t tokens (skip default TODO, FIXME) |
| `-f`, `--full-path` | display absolute dir/file path |
| `-s`, `--short` | display only token messages e.g. '#FIXME{3} - revist after release' - ignore longer snippets |
| `-r`, `--recursive` | traverse given dir path recursively |
| `-m`, `--max-depth N` | maximum depth of dir traversal - used with -r/--recursive flag |
| `-d`, `--debug` | enable debug mode |
| `-o`, `--out OUT` | path to output file, if existing dir is passed instead - TODO out file will be saved inside |
| `-v`, `--version` | show program's version number and exit |
