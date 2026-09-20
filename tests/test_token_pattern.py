import pytest

from todex.extractor import Extractor


def pattern(tokens=None, ignore_default=False):
    return Extractor.prepare_token_pattern(tokens or [], ignore_default)


def matched(pat, line: str) -> str | None:
    m = pat.search(line)
    return m.group() if m else None


def test_empty_with_ignore_default_raises():
    with pytest.raises(ValueError, match="no tokens"):
        pattern([], ignore_default=True)


@pytest.mark.parametrize(
    "tokens, ignore_default, line, expected",
    [
        ([], False, "# TODO: x", "TODO"),
        ([], False, "# FIXME: x", "FIXME"),
        (["WARN"], False, "# WARN: x", "WARN"),
        (["WARN"], False, "# TODO: x", "TODO"),
        (["WARN"], True, "# WARN: x", "WARN"),
        (["WARN"], True, "# TODO: x", None),
        (["WARN"], True, "# FIXME: x", None),
        (["WARN", "REVISIT"], True, "WARN here", "WARN"),
        (["WARN", "REVISIT"], True, "REVISIT later", "REVISIT"),
        (["TODO", "TODO", "FIXME"], False, "TODO", "TODO"),
        (["TODO", "TODO", "FIXME"], False, "FIXME", "FIXME"),
    ],
)
def test_prepare_token_pattern(tokens, ignore_default, line, expected):
    assert matched(pattern(tokens, ignore_default), line) == expected


@pytest.mark.parametrize(
    "line, expected",
    [
        ("todo: lower", "todo"),
        ("Todo: mixed", "Todo"),
        ("fIxMe: weird", "fIxMe"),
        ("TODO", "TODO"),
        ("#TODO: x", "TODO"),
        ("//FIXME x", "FIXME"),
        ("(TODO)", "TODO"),
        ("[FIXME]", "FIXME"),
        ("please TODO this soon", "TODO"),
        ("TODOS remaining", None),
        ("MYTODO done", None),
        ("XXTODOYY", None),
    ],
)
def test_word_boundaries_and_case(line, expected):
    assert matched(pattern(), line) == expected


def test_prefers_longer_token():
    pat = pattern(["FIX", "FIXME"], ignore_default=True)
    assert matched(pat, "FIXME: later") == "FIXME"
    assert matched(pat, "FIX: now") == "FIX"


@pytest.mark.parametrize(
    "tokens, line, expected",
    [
        (["C++"], "use C++ here", "C++"),
        (["file.txt"], "see file.txt now", "file.txt"),
        (["file.txt"], "fileXtxt", None),
        (["a.b*"], "a.b* value", "a.b*"),
        (["A+"], "A+", "A+"),
        (["A+"], "AAA", None),
        (["@FIXME"], "# @FIXME: x", "@FIXME"),
        (["@FIXME"], "# FIXME: bare", None),
        (["Do we need this!"], "# Do we need this!", "Do we need this!"),
        (["!!!URGENT!!!"], "# !!!URGENT!!!", "!!!URGENT!!!"),
    ],
)
def test_special_characters_are_literal(tokens, line, expected):
    assert matched(pattern(tokens, ignore_default=True), line) == expected
