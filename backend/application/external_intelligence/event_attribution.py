"""GAP-10: Deterministic event-attribution mappings.

Maps RiskSignalType → (EsgCategory, CSDDDRight) deterministically.
Used when creating ExternalRiskSignals to populate esg_category and
protected_right without LLM involvement (M43 audit requirement).
"""

from domain.enums import CSDDDRight, EsgCategory, RiskSignalType

# Primary protected right per signal type (most representative)
_SIGNAL_TO_RIGHT: dict[str, str] = {
    RiskSignalType.SANCTIONS.value:     CSDDDRight.MODERN_SLAVERY.value,
    RiskSignalType.CORRUPTION.value:    CSDDDRight.HUMAN_DIGNITY.value,
    RiskSignalType.LABOUR_RIGHTS.value: CSDDDRight.FORCED_LABOUR.value,
    RiskSignalType.ENVIRONMENTAL.value: CSDDDRight.ENVIRONMENTAL_DESTRUCTION.value,
    RiskSignalType.GOVERNANCE.value:    CSDDDRight.FREEDOM_OF_EXPRESSION.value,
}

_SIGNAL_TO_ESG: dict[str, str] = {
    RiskSignalType.SANCTIONS.value:     EsgCategory.GOVERNANCE.value,
    RiskSignalType.CORRUPTION.value:    EsgCategory.GOVERNANCE.value,
    RiskSignalType.LABOUR_RIGHTS.value: EsgCategory.SOCIAL.value,
    RiskSignalType.ENVIRONMENTAL.value: EsgCategory.ENVIRONMENTAL.value,
    RiskSignalType.GOVERNANCE.value:    EsgCategory.GOVERNANCE.value,
}


def derive_esg_category(signal_type: str) -> str | None:
    """Return EsgCategory value for a given RiskSignalType string."""
    return _SIGNAL_TO_ESG.get(signal_type)


def derive_protected_right(signal_type: str) -> str | None:
    """Return primary CSDDDRight value for a given RiskSignalType string."""
    return _SIGNAL_TO_RIGHT.get(signal_type)
