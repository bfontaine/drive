import pytest

from drive import sheets


@pytest.mark.parametrize("expected, lines", [
    ([], []),  # empty
    ([], [("a", "b", "c")]),  # only a header
    ([{"a": 1, "b": 2, "c": 3}], [("a", "b", "c"), (1, 2, 3)]),  # full line
    ([{"a": 1, "b": 2, "c": None}], [("a", "b", "c"), (1, 2)]),  # missing value
    ([{"a": 1, "b": 2, None: [3]}], [("a", "b"), (1, 2, 3)]),  # trailing value
    ([{"a": 1, "b": 2, None: [3, 4]}], [("a", "b"), (1, 2, 3, 4)]),  # trailing values
    # a mix of everything, please
    ([{"a": 1, "b": 1},
      {"a": 2, "b": 2},
      {"a": 3, "b": None},
      {"a": None, "b": None},
      {"a": None, "b": 5, None: ["five"]}],
     [("a", "b"),
      (1, 1), (2, 2), (3,), (), (None, 5, "five")]),
    # non-string field names
    ([{1: 42, False: 3}],
     [(1, False), (42, 3)]),
])
def test_sheet_lines_as_dicts_simple_cases(expected, lines):
    assert list(sheets.sheet_lines_as_dicts(lines)) == expected

    if lines:
        assert list(sheets.sheet_lines_as_dicts(lines[1:], fieldnames=lines[0])) == expected


@pytest.mark.parametrize("expected, lines", [
    ([], []),  # empty
    ([], [("a", "b", "c")]),  # only a header
    ([{"a": 1, "b": 2, "c": 3}], [("a", "b", "c"), (1, 2, 3)]),  # full line
    ([{"a": 1, "b": 2, "c": "no"}], [("a", "b", "c"), (1, 2)]),  # missing value
    ([{"a": 1, "b": 2, "k": [3]}], [("a", "b"), (1, 2, 3)]),  # trailing value
    ([{"a": 1, "b": 2, "k": [3, 4]}], [("a", "b"), (1, 2, 3, 4)]),  # trailing values
    # a mix of everything, please
    ([{"a": 1, "b": 1},
      {"a": 2, "b": 2},
      {"a": 3, "b": "no"},
      {"a": "no", "b": "no"},
      {"a": None, "b": 5, "k": ["five"]}],
     [("a", "b"),
      (1, 1), (2, 2), (3,), (), (None, 5, "five")]),
    # non-string field names
    ([{1: 42, False: 3}],
     [(1, False), (42, 3)]),
])
def test_sheet_lines_as_dicts_custom_restkey_restval(expected, lines):
    assert list(sheets.sheet_lines_as_dicts(lines, restkey="k", restval="no")) == expected

    if lines:
        assert list(sheets.sheet_lines_as_dicts(lines[1:], fieldnames=lines[0],
                                                restkey="k", restval="no")) == expected
