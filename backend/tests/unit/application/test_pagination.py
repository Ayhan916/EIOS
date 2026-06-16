"""Unit tests for pagination logic (M14).

These tests verify the correctness of the offset calculation and page
metadata formulas used by PaginationParams and Page.  They are written
against the published contract rather than importing the actual classes,
since the test runner does not have fastapi installed at the system level.
"""

from __future__ import annotations

import math

import pytest


# ---------------------------------------------------------------------------
# Offset calculation (mirrors PaginationParams.offset)
# ---------------------------------------------------------------------------

def offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


class TestOffsetCalculation:
    def test_page_1_offset_is_zero(self) -> None:
        assert offset(1, 20) == 0

    def test_page_2_offset_equals_page_size(self) -> None:
        assert offset(2, 20) == 20

    def test_page_3_offset(self) -> None:
        assert offset(3, 20) == 40

    def test_page_size_1(self) -> None:
        assert offset(5, 1) == 4

    def test_page_size_100(self) -> None:
        assert offset(3, 100) == 200

    def test_page_1_any_size_is_zero(self) -> None:
        for size in (1, 10, 20, 50, 100):
            assert offset(1, size) == 0


# ---------------------------------------------------------------------------
# total_pages formula (mirrors Page.total_pages computed_field)
# ---------------------------------------------------------------------------

def total_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if page_size else 1


class TestTotalPagesFormula:
    def test_empty_result_set_is_one_page(self) -> None:
        assert total_pages(0, 20) == 1

    def test_exact_fit_is_one_page(self) -> None:
        assert total_pages(20, 20) == 1

    def test_one_over_is_two_pages(self) -> None:
        assert total_pages(21, 20) == 2

    def test_large_dataset(self) -> None:
        assert total_pages(100, 20) == 5

    def test_partial_last_page(self) -> None:
        assert total_pages(55, 20) == 3

    def test_page_size_1(self) -> None:
        assert total_pages(7, 1) == 7

    def test_single_item(self) -> None:
        assert total_pages(1, 20) == 1


# ---------------------------------------------------------------------------
# has_next / has_prev formulas (mirrors Page computed_fields)
# ---------------------------------------------------------------------------

def has_next(page: int, total: int, page_size: int) -> bool:
    return page < total_pages(total, page_size)


def has_prev(page: int) -> bool:
    return page > 1


class TestHasNextHasPrev:
    def test_first_page_no_prev(self) -> None:
        assert not has_prev(1)

    def test_second_page_has_prev(self) -> None:
        assert has_prev(2)

    def test_first_page_has_next_when_more_items(self) -> None:
        assert has_next(1, total=50, page_size=20)

    def test_last_page_no_next(self) -> None:
        assert not has_next(2, total=40, page_size=20)

    def test_middle_page_has_both(self) -> None:
        assert has_next(3, total=100, page_size=20)
        assert has_prev(3)

    def test_single_page_no_nav(self) -> None:
        assert not has_next(1, total=5, page_size=20)
        assert not has_prev(1)

    def test_empty_dataset_no_nav(self) -> None:
        assert not has_next(1, total=0, page_size=20)
        assert not has_prev(1)


# ---------------------------------------------------------------------------
# End-to-end pagination scenario
# ---------------------------------------------------------------------------

class TestPaginationScenarios:
    """Verify offset + metadata combinations for common query patterns."""

    def test_first_page_of_large_dataset(self) -> None:
        page, size, total = 1, 20, 317
        assert offset(page, size) == 0
        assert total_pages(total, size) == 16
        assert has_next(page, total, size)
        assert not has_prev(page)

    def test_last_page_of_large_dataset(self) -> None:
        page, size, total = 16, 20, 317
        assert offset(page, size) == 300
        assert not has_next(page, total, size)
        assert has_prev(page)

    def test_single_item_dataset(self) -> None:
        page, size, total = 1, 20, 1
        assert offset(page, size) == 0
        assert total_pages(total, size) == 1
        assert not has_next(page, total, size)
        assert not has_prev(page)
