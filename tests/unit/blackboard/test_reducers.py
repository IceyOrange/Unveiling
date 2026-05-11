from __future__ import annotations

from blackboard.reducers import merge_dicts, merge_lists, replace


def test_merge_lists_appends():
    left = [1, 2]
    right = [3, 4]
    assert merge_lists(left, right) == [1, 2, 3, 4]


def test_merge_lists_empty_left():
    assert merge_lists([], [1, 2]) == [1, 2]


def test_merge_lists_empty_right():
    assert merge_lists([1, 2], []) == [1, 2]


def test_merge_lists_does_not_mutate():
    left = [1, 2]
    right = [3]
    result = merge_lists(left, right)
    assert left == [1, 2]
    assert right == [3]
    assert result == [1, 2, 3]


def test_merge_dicts_shallow_merge():
    left = {"a": 1, "b": 2}
    right = {"b": 3, "c": 4}
    assert merge_dicts(left, right) == {"a": 1, "b": 3, "c": 4}


def test_merge_dicts_does_not_mutate_left():
    left = {"a": 1}
    right = {"b": 2}
    result = merge_dicts(left, right)
    assert left == {"a": 1}
    assert result == {"a": 1, "b": 2}


def test_replace_scalar():
    assert replace(5, 10) == 10
    assert replace("old", "new") == "new"


def test_replace_none():
    assert replace("old", None) is None
