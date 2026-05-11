from typing import Any, TypeVar

T = TypeVar("T")


def merge_lists(left: list[T], right: list[T]) -> list[T]:
    """Reducer for list fields: append right to left."""
    return left + right


def merge_dicts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Reducer for dict fields: shallow merge with right overwriting left."""
    merged = left.copy()
    merged.update(right)
    return merged


def replace(left: T, right: T) -> T:
    """Reducer for scalar fields: replace with right."""
    return right
