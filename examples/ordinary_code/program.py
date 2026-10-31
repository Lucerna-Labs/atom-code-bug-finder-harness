"""Ordinary application function with a planted duplicate-counting defect."""


def distinct_total(values: list[int]) -> int:
    """Return the sum of distinct values."""
    return sum(values)  # Deliberate bug: repeated values are counted again.
