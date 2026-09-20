import pytest

from todex.extractor import Extractor


# --- tokens ---
def test_default_scan(sample, out, run):
    text = run(sample / "app.py", out)
    assert "TODO: main" in text
    assert "FIXME: bug" in text
    assert "WARN: careful" not in text


def test_t_adds_token_and_keeps_defaults(sample, out, run):
    text = run(sample / "app.py", out, tokens=["WARN"])
    assert "WARN: careful" in text
    assert "TODO: main" in text


def test_i_with_t_uses_only_custom_tokens(sample, out, run):
    text = run(sample / "app.py", out, tokens=["WARN"], ignore_default=True)
    assert "WARN: careful" in text
    assert "TODO: main" not in text


def test_custom_tokens_smoke(sample, out, run):
    """End-to-end: exotic token strings match through file scan."""
    text = run(
        sample / "custom_tokens.py",
        out,
        tokens=["NOTE", "!!!URGENT!!!", "@FIXME", "中文标记"],
        ignore_default=True,
    )
    assert "plain note" in text
    assert "!!!URGENT!!!" in text
    assert "at-prefixed fixme" in text
    assert "non-ascii" in text


# --- exclude / hidden / gitignore ---
def test_x_skips_patterns(sample, out, run):
    text = run(sample, out, exclude=["skip_me.py", "vendor/"], recursive=True)
    assert "TODO: skip" not in text
    assert "TODO: vendored" not in text
    assert "TODO: main" in text


def test_skips_hidden_and_dunder(sample, out, run):
    text = run(sample, out, recursive=True)
    assert "TODO: hidden" not in text
    assert "TODO: dunder" not in text


def test_H_includes_hidden_and_dunder(sample, out, run):
    text = run(sample, out, include_hidden=True, recursive=True)
    assert "TODO: hidden" in text
    assert "TODO: dunder" in text


def test_g_applies_gitignore_and_default_hidden(sample, out, run):
    text = run(sample, out, use_gitignore=True, recursive=True)
    assert "TODO: vendored" not in text
    assert "TODO: skip" not in text
    assert "TODO: main" in text
    assert "TODO: hidden" not in text


def test_g_with_H_includes_hidden_but_keeps_gitignore(sample, out, run):
    text = run(sample, out, use_gitignore=True, include_hidden=True, recursive=True)
    assert "TODO: hidden" in text
    assert "TODO: vendored" not in text
    assert "TODO: venv" in text  # .venv not in .gitignore, .* default off via -H


def test_g_with_x_bang_reincludes_vendor(sample, out, run):
    text = run(
        sample,
        out,
        use_gitignore=True,
        exclude=["!vendor/", "!vendor/**"],
        recursive=True,
    )
    assert "TODO: vendored" in text


def test_g_missing_gitignore_is_noop(sample, run):
    bare = sample / "bare"
    text = run(bare, bare / "out.txt", use_gitignore=True)
    assert "TODO: bare" in text


def test_file_path_g_is_noop_but_still_processes(sample, out, run):
    # -g only loads .gitignore for directory scans -> explicit file PATH is always processed
    patterns = Extractor(
        path=sample / "app.py",
        use_gitignore=True,
        out=str(out),
    ).get_gitignore_patterns()
    assert patterns == []

    text = run(sample / "app.py", out, use_gitignore=True)
    assert "TODO: main" in text


# --- recursion ---
def test_r_finds_nested(sample, out, run):
    text = run(sample, out, recursive=True)
    assert "TODO: deep" in text
    assert "TODO: deeper" in text


def test_r_m_limits_depth(sample, out, run):
    text = run(sample, out, recursive=True, max_depth=1)
    assert "TODO: deep" in text
    assert "TODO: deeper" not in text


def test_without_r_skips_nested(sample, out, run):
    text = run(sample, out)
    assert "TODO: deep" not in text
    assert "TODO: main" in text


# --- short / snippets ---
def test_s_omits_snippet_body(sample, out, run):
    text = run(sample / "snippet.py", out, short=True)
    assert "FIXME" in text
    assert "return 1" not in text


def test_snippet_includes_following_lines(sample, out, run):
    text = run(sample / "snippet.py", out)
    assert "return 1" in text


def test_warn_snippet_count(tmp_path, run):
    src = tmp_path / "warn.py"
    out = tmp_path / "out.txt"
    src.write_text("# WARN{2} check this\nx = 1\ny = 2\n", encoding="utf-8")
    text = run(src, out, tokens=["WARN"], ignore_default=True)
    assert "WARN" in text
    assert "x = 1" in text
    assert "y = 2" not in text


def test_snippet_past_eof_does_not_crash(tmp_path, run):
    src = tmp_path / "short.py"
    out = tmp_path / "out.txt"
    src.write_text("# TODO{10} almost eof\nonly one more\n", encoding="utf-8")
    text = run(src, out)
    assert "TODO" in text
    assert "only one more" in text


def test_get_snippet_count_default_one():
    line = "# TODO: x"
    start = line.index("TODO") + len("TODO")
    assert Extractor.get_snippet_count(line, start=start) == 1


def test_get_snippet_count_parses_braces():
    line = "# TODO{3} x"
    assert Extractor.get_snippet_count(line, start=line.index("{")) == 3


@pytest.mark.parametrize(
    "content, match",
    [
        ("# TODO{3 no close\n", "invalid snippet count"),
        ("# TODO{abc}\n", None),
    ],
)
def test_invalid_snippet_raises(tmp_path, content, match):
    src = tmp_path / "bad.py"
    out = tmp_path / "out.txt"
    src.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        Extractor(path=src, out=str(out)).run()


def test_multiple_hits_one_header_and_line_numbers(tmp_path, run):
    src = tmp_path / "multi.py"
    out = tmp_path / "out.txt"
    src.write_text(
        "line1\n# TODO{2} first\nbody\n# FIXME: second\n",
        encoding="utf-8",
    )
    text = run(src, out)
    assert text.count("======================") == 1
    assert "line 2:" in text
    assert "line 4:" in text
    assert "TODO" in text
    assert "FIXME" in text
    assert "body" in text


# --- paths / out / binary / errors ---
def test_f_writes_absolute_path(sample, out, run):
    target = sample / "app.py"
    text = run(target, out, full_path=True)
    assert str(target.absolute()) in text


def test_o_dir_writes_todo_inside(sample):
    reports = sample / "reports"
    reports.mkdir()
    Extractor(path=sample / "app.py", out=str(reports)).run()
    todo = reports / "TODO"
    assert todo.is_file()
    assert "TODO: main" in todo.read_text(encoding="utf-8")


def test_does_not_rescan_output_file(sample):
    """Output path must be skipped so a prior TODO file is not re-ingested."""
    out = sample / "TODO"
    out.write_text(
        "======================\nstale.py\n\tline 1: # TODO: from previous run\n",
        encoding="utf-8",
    )
    Extractor(path=sample, out=str(out), recursive=True).run()
    text = out.read_text(encoding="utf-8")
    assert "TODO: from previous run" not in text
    assert "TODO: main" in text


def test_skips_undecodable_file_and_continues(tmp_path, capsys, run):
    (tmp_path / "good.py").write_text("# TODO: keep me\n", encoding="utf-8")
    (tmp_path / "bad.bin").write_bytes(b"\xff\xfe TODO: binary\n")
    text = run(tmp_path, tmp_path / "out.txt")
    assert "TODO: keep me" in text
    err = capsys.readouterr().err
    assert "skipping" in err
    assert "bad.bin" in err


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Extractor(path=tmp_path / "missing", out=str(tmp_path / "out.txt")).run()
