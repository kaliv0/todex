import sys

import pytest

from tests.helpers import broken_pipe_write, patch_stdout_broken_flush, write_good_and_bad
from todex.extractor import DEFAULT_MAX_DEPTH, Extractor
from todex.writer import StopExtractionError


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
    # end-to-end: exotic token strings match through file scan
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


def test_exclude_spec_defaults_bang_and_comments(tmp_path):
    out = tmp_path / "out.txt"
    ext = Extractor(
        path=tmp_path,
        out=str(out),
        exclude=["vendor/", "!vendor/keep.py", "# comment", "", "  "],
    )
    spec = ext.exclude_spec

    assert spec.match_file(".hidden.py")
    assert spec.match_file("__init__.py")
    assert any(spec.match_files(["vendor", "vendor/"]))
    assert spec.match_file("vendor/lib.py")
    assert not spec.match_file("vendor/keep.py")
    assert not spec.match_file("app.py")


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
    )._get_gitignore_patterns()
    assert patterns == []

    text = run(sample / "app.py", out, use_gitignore=True)
    assert "TODO: main" in text


# --- recursion ---
def test_dir_walk_order_files_then_dirs_by_name(tmp_path):
    for name in ("c.py", "a.py", "b.py"):
        (tmp_path / name).write_text(f"# TODO: {name}\n", encoding="utf-8")
    nested = tmp_path / "d"
    nested.mkdir()
    (nested / "z.py").write_text("# TODO: nested\n", encoding="utf-8")

    out = tmp_path / "out.txt"
    Extractor(path=tmp_path, out=str(out), recursive=True).run()

    text = out.read_text(encoding="utf-8")
    assert text.index("TODO: a.py") < text.index("TODO: b.py") < text.index("TODO: c.py")
    assert text.index("TODO: c.py") < text.index("TODO: nested")


def test_r_finds_nested(sample, out, run):
    text = run(sample, out, recursive=True)
    assert "TODO: deep" in text
    assert "TODO: deeper" in text


def test_r_m_limits_depth(sample, out, run):
    text = run(sample, out, recursive=True, max_depth=1)
    assert "TODO: deep" in text
    assert "TODO: deeper" not in text


@pytest.mark.parametrize("max_depth", [0, -1])
def test_max_depth_rejects_non_positive(tmp_path, max_depth):
    with pytest.raises(ValueError, match="max_depth must be a positive integer"):
        Extractor(path=tmp_path, max_depth=max_depth)


def test_max_depth_none_uses_default(tmp_path):
    assert Extractor(path=tmp_path).max_depth == DEFAULT_MAX_DEPTH


def test_without_r_skips_nested(sample, out, run):
    text = run(sample, out)
    assert "TODO: deep" not in text
    assert "TODO: main" in text


@pytest.mark.parametrize(
    "link_name, target_is_dir, recursive, hidden",
    [
        ("linkdir", True, True, "TODO: through-symlink"),
        ("link.py", False, False, "TODO: via-file-link"),
    ],
    ids=["dir", "file"],
)
def test_symlink_not_followed(tmp_path, link_name, target_is_dir, recursive, hidden):
    outside = tmp_path / "outside"
    outside.mkdir()
    if target_is_dir:
        (outside / "via_link.py").write_text(f"# {hidden}\n", encoding="utf-8")
        target = outside
    else:
        target = outside / "target.py"
        target.write_text(f"# {hidden}\n", encoding="utf-8")

    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "top.py").write_text("# TODO: top\n", encoding="utf-8")
    (scan / link_name).symlink_to(target)

    out = scan / "out.txt"
    Extractor(path=scan, out=str(out), recursive=recursive).run()

    text = out.read_text(encoding="utf-8")
    assert "TODO: top" in text
    assert hidden not in text


# --- concise / snippets ---
def test_c_omits_snippet_body(sample, out, run):
    text = run(sample / "snippet.py", out, concise=True)
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


@pytest.mark.parametrize(
    "line, expected",
    [
        ("# TODO: x", 1),
        ("# TODO{3} x", 3),
    ],
)
def test_get_snippet_count_after_token(line, expected):
    token_end = line.index("TODO") + len("TODO")
    assert (
        Extractor(path=".")._get_snippet_count_after_token(line, token_end=token_end, line_num=1) == expected
    )


@pytest.mark.parametrize(
    "content",
    [
        "# TODO{3 no close\n",
        "# TODO{abc}\n",
    ],
)
@pytest.mark.parametrize("concise", [False, True], ids=["full", "concise"])
def test_invalid_snippet_raises(tmp_path, content, concise):
    src = tmp_path / "bad.py"
    out = tmp_path / "out.txt"
    src.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid snippet count"):
        Extractor(path=src, out=str(out), concise=concise).run()


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


# --- paths / out / stdout / tee / binary / errors ---
def test_f_writes_absolute_path(sample, out, run):
    target = sample / "app.py"
    text = run(target, out, full_path=True)
    assert str(target.absolute()) in text


def test_o_dir_writes_todo_inside(sample, app_out):
    reports = sample / "reports"
    reports.mkdir()
    Extractor(path=sample / "app.py", out=str(reports)).run()
    assert (reports / "TODO").read_text(encoding="utf-8") == app_out


def test_omitted_out_defaults_to_todo(sample, monkeypatch, app_out):
    monkeypatch.chdir(sample)
    Extractor(path="app.py").run()
    assert (sample / "TODO").read_text(encoding="utf-8") == app_out


def test_s_writes_to_stdout_only(sample, capsys, app_out):
    Extractor(path=sample / "app.py", stdout=True).run()
    assert capsys.readouterr().out == app_out
    assert not (sample / "TODO").exists()


def test_tee_writes_stdout_and_file(sample, out, capsys, app_out):
    Extractor(path=sample / "app.py", out=str(out), tee=True).run()
    assert out.read_text(encoding="utf-8") == app_out
    assert capsys.readouterr().out == app_out


def test_tee_without_out_uses_todo(sample, monkeypatch, capsys, app_out):
    monkeypatch.chdir(sample)
    Extractor(path="app.py", tee=True).run()
    assert (sample / "TODO").read_text(encoding="utf-8") == app_out
    assert capsys.readouterr().out == app_out


def test_tee_survives_broken_stdout(sample, out, monkeypatch, app_out):
    # pipe reader gone -> stdout fails, file side still gets the full result
    monkeypatch.setattr(sys.stdout, "write", broken_pipe_write)
    Extractor(path=sample / "app.py", out=str(out), tee=True).run()
    assert out.read_text(encoding="utf-8") == app_out


def test_s_stops_on_broken_stdout(tmp_path, monkeypatch):
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text("# TODO: x\n", encoding="utf-8")

    monkeypatch.setattr(sys.stdout, "write", broken_pipe_write)
    seen = []
    orig = Extractor.process_file

    def counted(self, path) -> None:
        seen.append(path)
        orig(self, path)

    monkeypatch.setattr(Extractor, "process_file", counted)
    with pytest.raises(StopExtractionError):
        Extractor(path=tmp_path, stdout=True).run()
    assert len(seen) == 1


@pytest.mark.parametrize("relative", [False, True], ids=["abs", "relative"])
def test_does_not_rescan_output_file(sample, monkeypatch, stale_todo, relative):
    # NB: Output path must be skipped so a prior TODO file is not re-ingested
    out = sample / "TODO"
    out.write_text(stale_todo, encoding="utf-8")

    if relative:
        monkeypatch.chdir(sample)
        Extractor(path=".", out="./TODO", recursive=True).run()
    else:
        Extractor(path=sample, out=str(out), recursive=True).run()

    text = out.read_text(encoding="utf-8")
    assert "TODO: from previous run" not in text
    assert "TODO: main" in text


def test_stdout_has_no_out_skip(tmp_path, capsys):
    todo = tmp_path / "TODO"
    todo.write_text("# TODO: keep scanning me\n", encoding="utf-8")

    Extractor(path=tmp_path, stdout=True).run()

    assert "TODO: keep scanning me" in capsys.readouterr().out


@pytest.mark.parametrize(
    "name, content",
    [("empty.py", ""), ("nl.py", "\n")],
    ids=["empty", "newline"],
)
def test_zero_token_file_empty_out(tmp_path, name, content):
    src = tmp_path / name
    src.write_text(content, encoding="utf-8")
    out = tmp_path / "out.txt"

    Extractor(path=src, out=str(out)).run()

    assert out.read_text(encoding="utf-8") == ""


def test_o_equals_scanned_file_truncates(tmp_path):
    src = tmp_path / "f.py"
    src.write_text("# TODO: will be truncated\n", encoding="utf-8")

    Extractor(path=src, out=str(src)).run()

    assert src.read_text(encoding="utf-8") == ""


def test_zero_hit_scan_truncates_stale_out(tmp_path):
    src = tmp_path / "empty.py"
    src.write_text("print(1)\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    out.write_text("stale from previous run\n", encoding="utf-8")
    Extractor(path=src, out=str(out)).run()
    assert out.read_text(encoding="utf-8") == ""


def test_debug_emits_processing_trail(sample, out, capsys):
    Extractor(path=sample / "app.py", out=str(out), debug=True).run()

    debug_out = capsys.readouterr().out
    assert debug_out.startswith("processing:\n")
    assert "\tapp.py\n" in debug_out


@pytest.mark.parametrize("debug", [True, False], ids=["debug", "silent"])
def test_skips_undecodable_file_and_continues(tmp_path, capsys, run, debug):
    write_good_and_bad(tmp_path)

    text = run(tmp_path, tmp_path / "out.txt", debug=debug)

    assert "TODO: keep me" in text
    err = capsys.readouterr().err
    if debug:
        assert "skipping" in err
        assert "bad.bin" in err
        assert "utf-8" in err
    else:
        assert err == ""


def test_skips_undecodable_mid_file_keeps_prior_hits(tmp_path, capsys):
    src = tmp_path / "mixed.py"
    # pad so the UTF-8 decoder can emit the hit line before failing later
    src.write_bytes(b"# TODO: first\n" + b"x" * 10000 + b"\n\xff\xfe bad\n")
    out = tmp_path / "out.txt"

    Extractor(path=src, out=str(out), debug=True).run()
    assert "TODO: first" in out.read_text(encoding="utf-8")

    err = capsys.readouterr().err
    assert "skipping" in err
    assert "mixed.py" in err


def test_s_stops_on_broken_flush(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("# TODO: x\n", encoding="utf-8")
    patch_stdout_broken_flush(monkeypatch)

    with pytest.raises(StopExtractionError):
        Extractor(path=tmp_path, stdout=True).run()


def test_tee_survives_broken_flush(sample, out, monkeypatch, app_out):
    patch_stdout_broken_flush(monkeypatch)

    Extractor(path=sample / "app.py", out=str(out), tee=True).run()

    assert out.read_text(encoding="utf-8") == app_out


def test_debug_broken_pipe_raises_broken_pipe(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("# TODO: x\n", encoding="utf-8")
    monkeypatch.setattr(sys.stdout, "write", broken_pipe_write)

    with pytest.raises(BrokenPipeError):
        Extractor(path=tmp_path, out=str(tmp_path / "out.txt"), debug=True).run()


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Extractor(path=tmp_path / "missing", out=str(tmp_path / "out.txt")).run()
