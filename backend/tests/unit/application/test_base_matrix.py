"""Tests for CSDDD base risk matrix (TASK-003 Phase 2)."""

from __future__ import annotations

import pytest

from application.sector_intelligence.base_matrix import (
    BASE_MATRIX,
    CALIBRATED_NACE_CODES,
    CALIBRATION_VERSION,
    get_score,
    get_scores,
    is_calibrated,
)
from domain.enums import CSDDDRight


class TestBaseMatrixIntegrity:
    def test_has_20_calibrated_sectors(self) -> None:
        assert len(BASE_MATRIX) == 20

    def test_all_calibrated_codes_in_nace_taxonomy(self) -> None:
        from application.sector_intelligence.nace_taxonomy import NACE_2DIGIT
        for code in BASE_MATRIX:
            assert code in NACE_2DIGIT, f"NACE {code} not in taxonomy"

    def test_every_sector_has_all_21_rights(self) -> None:
        for code, scores in BASE_MATRIX.items():
            for right in CSDDDRight:
                assert right in scores, f"NACE {code} missing right {right.value}"
            assert len(scores) == 21, f"NACE {code} has {len(scores)} rights, expected 21"

    def test_all_scores_in_range_1_to_10(self) -> None:
        for code, scores in BASE_MATRIX.items():
            for right, score in scores.items():
                assert 1 <= score <= 10, (
                    f"NACE {code} / {right.value}: score {score} out of range [1, 10]"
                )

    def test_all_scores_are_integers(self) -> None:
        for code, scores in BASE_MATRIX.items():
            for right, score in scores.items():
                assert isinstance(score, int), (
                    f"NACE {code} / {right.value}: score {score!r} is not int"
                )

    def test_calibrated_nace_codes_matches_base_matrix(self) -> None:
        assert sorted(CALIBRATED_NACE_CODES) == sorted(BASE_MATRIX.keys())

    def test_calibration_version_format(self) -> None:
        assert CALIBRATION_VERSION.startswith("v")


class TestKnownScores:
    """Spot-check curated scores against documented sources."""

    def test_textiles_forced_labour_is_high(self) -> None:
        # KnowTheChain 2023: textiles worst performer
        score = get_score("13", CSDDDRight.FORCED_LABOUR)
        assert score >= 8, f"Textiles forced labour should be >= 8, got {score}"

    def test_agriculture_child_labour_is_critical(self) -> None:
        # ILO: 170M child labourers in agriculture
        score = get_score("01", CSDDDRight.CHILD_LABOUR)
        assert score >= 8, f"Agriculture child labour should be >= 8, got {score}"

    def test_it_consulting_forced_labour_is_low(self) -> None:
        score = get_score("62", CSDDDRight.FORCED_LABOUR)
        assert score <= 2, f"IT forced labour should be <= 2, got {score}"

    def test_it_consulting_privacy_is_elevated(self) -> None:
        # IT sector has structural privacy risk
        score = get_score("62", CSDDDRight.PRIVACY)
        assert score >= 5, f"IT privacy should be >= 5, got {score}"

    def test_mining_occupational_safety_is_high(self) -> None:
        score = get_score("07", CSDDDRight.OCCUPATIONAL_SAFETY)
        assert score >= 8, f"Metal mining safety should be >= 8, got {score}"

    def test_mining_mercury_is_elevated(self) -> None:
        # Artisanal gold mining: Minamata Convention
        score = get_score("07", CSDDDRight.MERCURY)
        assert score >= 7, f"Metal mining mercury should be >= 7, got {score}"

    def test_logistics_working_hours_is_high(self) -> None:
        # OECD: road freight high-risk for labour hours
        score = get_score("49", CSDDDRight.WORKING_HOURS)
        assert score >= 7, f"Logistics working hours should be >= 7, got {score}"

    def test_automotive_lower_than_textiles_for_forced_labour(self) -> None:
        automotive = get_score("29", CSDDDRight.FORCED_LABOUR)
        textiles = get_score("13", CSDDDRight.FORCED_LABOUR)
        assert automotive < textiles


class TestGetScores:
    def test_returns_all_21_rights(self) -> None:
        scores = get_scores("29")
        assert len(scores) == 21
        for right in CSDDDRight:
            assert right in scores

    def test_uncalibrated_code_returns_fallback(self) -> None:
        # NACE 34 does not exist in NACE Rev.2; any unknown returns fallback
        scores = get_scores("34")
        assert len(scores) == 21
        for score in scores.values():
            assert 1 <= score <= 10

    def test_calibrated_code_returns_curated_scores(self) -> None:
        scores = get_scores("13")
        assert scores[CSDDDRight.FORCED_LABOUR] == 9  # curated value

    def test_is_calibrated_true_for_known_code(self) -> None:
        assert is_calibrated("29") is True
        assert is_calibrated("13") is True
        assert is_calibrated("01") is True

    def test_is_calibrated_false_for_unknown(self) -> None:
        assert is_calibrated("34") is False
        assert is_calibrated("00") is False

    def test_scores_dict_is_not_mutated_between_calls(self) -> None:
        scores1 = get_scores("29")
        scores1[CSDDDRight.CHILD_LABOUR] = 99  # mutate the returned dict
        scores2 = get_scores("29")
        assert scores2[CSDDDRight.CHILD_LABOUR] != 99  # original unaffected
