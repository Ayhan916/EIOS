"""Unit tests for ESG pillar classifier (M28)."""

import pytest

from application.scoring.esg_categorizer import categorize_pillar


class TestCategorizePillar:
    def test_environmental_keyword_in_category(self) -> None:
        assert categorize_pillar("Climate Change") == "Environmental"

    def test_environmental_keyword_energy(self) -> None:
        assert categorize_pillar("Energy Consumption") == "Environmental"

    def test_environmental_keyword_carbon(self) -> None:
        assert categorize_pillar("carbon emissions", "") == "Environmental"

    def test_environmental_keyword_water(self) -> None:
        assert categorize_pillar("water usage risk") == "Environmental"

    def test_environmental_keyword_waste(self) -> None:
        assert categorize_pillar("Waste Management") == "Environmental"

    def test_environmental_keyword_biodiversity(self) -> None:
        assert categorize_pillar("biodiversity impact") == "Environmental"

    def test_social_keyword_labor(self) -> None:
        assert categorize_pillar("Labor Rights") == "Social"

    def test_social_keyword_health_safety(self) -> None:
        assert categorize_pillar("Health & Safety") == "Social"

    def test_social_keyword_human_rights(self) -> None:
        assert categorize_pillar("human rights violation") == "Social"

    def test_social_keyword_diversity(self) -> None:
        assert categorize_pillar("Diversity & Inclusion") == "Social"

    def test_social_keyword_modern_slavery(self) -> None:
        assert categorize_pillar("modern slavery risk") == "Social"

    def test_governance_default(self) -> None:
        assert categorize_pillar("Board Oversight") == "Governance"

    def test_governance_compliance(self) -> None:
        assert categorize_pillar("Regulatory Compliance") == "Governance"

    def test_governance_bribery(self) -> None:
        assert categorize_pillar("Anti-Bribery Controls") == "Governance"

    def test_governance_empty_category(self) -> None:
        assert categorize_pillar("") == "Governance"

    def test_title_fallback_used(self) -> None:
        # Category is generic but title contains keyword
        assert categorize_pillar("Risk", "Carbon footprint reduction") == "Environmental"

    def test_category_takes_precedence_when_both_present(self) -> None:
        # Category matches Environmental → wins
        assert categorize_pillar("climate risk", "labor issue") == "Environmental"

    def test_case_insensitive(self) -> None:
        assert categorize_pillar("ENVIRONMENTAL COMPLIANCE") == "Environmental"
        assert categorize_pillar("LABOR STANDARDS") == "Social"
