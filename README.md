<div align="center">
  <img src="https://github.com/kaliv0/todex/blob/main/assets/truck.jpg?raw=true" width="400" alt="Todex">
</div>

# todex

![Python 3.X](https://img.shields.io/badge/python-^3.12-blue?style=flat-square&logo=Python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/todex.svg)](https://pypi.org/project/todex/)
[![Downloads](https://static.pepy.tech/badge/todex)](https://pepy.tech/projects/todex)

Peak mud digger and TODO extractor

```text
usage: todex [-h] [-x [PATTERN ...]] [-H] [-t [TOKEN ...]] [-i] [-f] [-s] [-r] [-m N] [-d] [-o OUT] [-v] PATH

positional arguments:
    PATH                  path to file or dir to process    

options:
    -h, --help            show this help message and exit
    -x, --exclude [PATTERN ...]
                          git-like patterns to skip (paths, names, or globs together with default .* / __*), e.g.
    
                              bar.py       any file named bar.py
                              /bar.py      only top-level
                              foo/bar.py   path under the scan root
                              vendor/      directory and its contents
                              **/*.pyc     nested matches
                              !fizz.md     re-include after a broader exclude

    -H, --include-hidden  do not apply default excludes for hidden names (.* / __*)
    -t, --tokens [TOKEN ...]
                          list of tokens to search for (together with default TODO, FIXME) e.g. WARN, REVISIT. 
                          If the token is followed by {lines-count} e.g. #FIXME{3} 
                          the extractor will include multiline snippet with the length specified between the curly braces: 
                        
                              #FIXME{3} - revist after release 
                              if self.foo == "bar": 
                                  return f"fizz{buzz}"
                                
    -i, --ignore-default  use only -t tokens (skip default TODO, FIXME)
    -f, --full-path       display absolute dir/file path
    -s, --short           display only token messages e.g. '#TODO: after release', ignore longer snippets
    -r, --recursive       traverse given dir path recursively
    -m, --max-depth N     maximum depth of dir traversal - used with -r/--recursive flag
    -d, --debug           enable debug mode
    -o, --out OUT         path to output file, if existing dir is passed instead - TODO out file will be saved inside
    -v, --version         show program's version number and exit

```
