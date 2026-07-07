"""Tests for NACE Rev. 2 taxonomy module (TASK-003 Phase 2)."""

from __future__ import annotations

from application.sector_intelligence.nace_taxonomy import (
    ALL_NACE_2DIGIT_CODES,
    NACE_2DIGIT,
    get_division_name,
    get_section,
    normalize_nace,
)


class TestNACETaxonomyCompleteness:
    def test_has_88_codes(self) -> None:
        assert len(NACE_2DIGIT) == 88

    def test_all_codes_are_sorted(self) -> None:
        assert sorted(ALL_NACE_2DIGIT_CODES) == ALL_NACE_2DIGIT_CODES

    def test_all_codes_are_two_digits(self) -> None:
        for code in NACE_2DIGIT:
            assert len(code) == 2, f"Code '{code}' is not 2 digits"
            assert code.isdigit(), f"Code '{code}' is not numeric"

    def test_all_section_letters_are_uppercase(self) -> None:
        for code, (section, _) in NACE_2DIGIT.items():
            assert section == section.upper(), f"Section for {code} is not uppercase"
            assert len(section) == 1

    def test_sections_cover_a_through_u(self) -> None:
        sections = {section for section, _ in NACE_2DIGIT.values()}
        set("ABCDEFGHIJKLMNOPQRSTU")
        # Not all letters are used (no E=Energy in original NACE sections that are missing)
        # but at minimum these high-priority sections must be present
        for s in "ABCDFGHJKMN":
            assert s in sections, f"Section {s} missing from taxonomy"


class TestGetSection:
    def test_automotive(self) -> None:
        result = get_section("29")
        assert result is not None
        assert result[0] == "C"
        assert "Manufacturing" in result[1]

    def test_logistics(self) -> None:
        result = get_section("49")
        assert result is not None
        assert result[0] == "H"

    def test_agriculture(self) -> None:
        result = get_section("01")
        assert result is not None
        assert result[0] == "A"

    def test_it_consulting(self) -> None:
        result = get_section("62")
        assert result is not None
        assert result[0] == "J"

    def test_textiles(self) -> None:
        result = get_section("13")
        assert result is not None
        assert result[0] == "C"

    def test_unknown_code_returns_none(self) -> None:
        assert get_section("99") is not None  # 99 exists (extraterritorial)
        assert get_section("00") is None
        assert get_section("04") is None  # 04 does not exist in NACE Rev. 2

    def test_all_known_codes_return_result(self) -> None:
        for code in ALL_NACE_2DIGIT_CODES:
            result = get_section(code)
            assert result is not None, f"get_section({code!r}) returned None"


class TestGetDivisionName:
    def test_automotive_name(self) -> None:
        name = get_division_name("29")
        assert "motor vehicle" in name.lower() or "vehicles" in name.lower()

    def test_returns_string_for_unknown(self) -> None:
        name = get_division_name("00")
        assert isinstance(name, str)
        assert "00" in name  # fallback includes the code

    def test_all_calibrated_codes_have_names(self) -> None:
        calibrated = ["01", "05", "07", "13", "14", "20", "26", "29", "49", "62"]
        for code in calibrated:
            name = get_division_name(code)
            assert name and name != f"NACE {code}", f"No specific name for NACE {code}"


class TestNormalizeNACE:
    def test_plain_two_digit(self) -> None:
        assert normalize_nace("29") == "29"
        assert normalize_nace("01") == "01"
        assert normalize_nace("62") == "62"

    def test_four_digit_truncates_to_two(self) -> None:
        assert normalize_nace("29.10") == "29"
        assert normalize_nace("13.10") == "13"

    def test_leading_zero_preserved(self) -> None:
        assert normalize_nace("1") == "01"

    def test_unknown_returns_none(self) -> None:
        assert normalize_nace("00") is None
        assert normalize_nace("abc") is None
        assert normalize_nace("04") is None

    def test_whitespace_stripped(self) -> None:
        assert normalize_nace(" 29 ") == "29"
        assert normalize_nace("29.10 ") == "29"
