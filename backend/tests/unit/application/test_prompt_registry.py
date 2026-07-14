"""Tests for application/prompt_registry.py — ADR-011.

Invariants tested:
  - get_active() returns PromptVersion when DB has an active row
  - get_active() returns None when no active row exists
  - get() returns PromptVersion for specific version
  - get() returns None for unknown prompt/version
  - render() substitutes declared variables correctly
  - render() raises KeyError on missing variable
  - render() handles template with no variables (empty dict)
  - PromptVersion is a frozen value object
  - _to_domain() maps model fields correctly
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.prompt_registry import PromptRegistry
from domain.prompt_version import PromptVersion
from infrastructure.persistence.models.prompt_version import PromptVersionModel

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc)


# ── helpers ───────────────────────────────────────────────────────────────────

def _model(
    prompt_name: str = "test_prompt",
    version: int = 1,
    template: str = "Hello {name}",
    variables: list[str] | None = None,
    active: bool = True,
) -> PromptVersionModel:
    m = MagicMock(spec=PromptVersionModel)
    m.prompt_name = prompt_name
    m.version = version
    m.template = template
    m.variables = variables or ["name"]
    m.active = active
    m.created_at = _NOW
    return m


def _session_returning(row: PromptVersionModel | None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)
    return session


def _domain_version(
    template: str = "Hello {name}",
    variables: tuple[str, ...] = ("name",),
    version: int = 1,
) -> PromptVersion:
    return PromptVersion(
        prompt_name="test_prompt",
        version=version,
        template=template,
        variables=variables,
        active=True,
        created_at=_NOW,
    )


# ── get_active ────────────────────────────────────────────────────────────────

class TestGetActive:
    @pytest.mark.asyncio
    async def test_returns_prompt_version_when_found(self) -> None:
        session = _session_returning(_model())
        registry = PromptRegistry(session)
        result = await registry.get_active("test_prompt")
        assert isinstance(result, PromptVersion)
        assert result.prompt_name == "test_prompt"
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_no_active_row(self) -> None:
        session = _session_returning(None)
        registry = PromptRegistry(session)
        result = await registry.get_active("nonexistent_prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_maps_template_correctly(self) -> None:
        session = _session_returning(_model(template="System: {context}"))
        registry = PromptRegistry(session)
        result = await registry.get_active("test_prompt")
        assert result is not None
        assert result.template == "System: {context}"

    @pytest.mark.asyncio
    async def test_maps_variables_as_tuple(self) -> None:
        session = _session_returning(_model(variables=["company", "year"]))
        registry = PromptRegistry(session)
        result = await registry.get_active("test_prompt")
        assert result is not None
        assert result.variables == ("company", "year")


# ── get (specific version) ────────────────────────────────────────────────────

class TestGetVersion:
    @pytest.mark.asyncio
    async def test_returns_specific_version(self) -> None:
        session = _session_returning(_model(version=3))
        registry = PromptRegistry(session)
        result = await registry.get("test_prompt", 3)
        assert result is not None
        assert result.version == 3

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_version(self) -> None:
        session = _session_returning(None)
        registry = PromptRegistry(session)
        result = await registry.get("test_prompt", 99)
        assert result is None


# ── render ────────────────────────────────────────────────────────────────────

class TestRender:
    def test_renders_template_with_variables(self) -> None:
        pv = _domain_version(template="Hello {name}, year is {year}", variables=("name", "year"))
        registry = PromptRegistry(AsyncMock())
        rendered = registry.render(pv, {"name": "BMW AG", "year": "2024"})
        assert rendered == "Hello BMW AG, year is 2024"

    def test_renders_template_with_no_variables(self) -> None:
        pv = _domain_version(template="Static prompt text.", variables=())
        registry = PromptRegistry(AsyncMock())
        rendered = registry.render(pv, {})
        assert rendered == "Static prompt text."

    def test_raises_key_error_on_missing_variable(self) -> None:
        pv = _domain_version(template="Hello {name}", variables=("name",))
        registry = PromptRegistry(AsyncMock())
        with pytest.raises(KeyError, match="name"):
            registry.render(pv, {})

    def test_extra_variables_do_not_cause_error(self) -> None:
        pv = _domain_version(template="Hello {name}", variables=("name",))
        registry = PromptRegistry(AsyncMock())
        # extra keys in variables dict are ignored
        rendered = registry.render(pv, {"name": "ACME", "unused": "value"})
        assert rendered == "Hello ACME"

    def test_error_message_contains_missing_variable_name(self) -> None:
        pv = _domain_version(template="{a} and {b}", variables=("a", "b"))
        registry = PromptRegistry(AsyncMock())
        with pytest.raises(KeyError) as exc_info:
            registry.render(pv, {"a": "present"})
        assert "b" in str(exc_info.value)


# ── value object contract ─────────────────────────────────────────────────────

class TestValueObjectContract:
    def test_prompt_version_is_frozen(self) -> None:
        pv = _domain_version()
        with pytest.raises((AttributeError, TypeError)):
            pv.version = 99  # type: ignore[misc]

    def test_prompt_version_equality_by_value(self) -> None:
        pv1 = _domain_version()
        pv2 = _domain_version()
        assert pv1 == pv2

    def test_to_domain_maps_all_fields(self) -> None:
        model = _model(
            prompt_name="fin_sys",
            version=2,
            template="Extract {metric}",
            variables=["metric"],
            active=False,
        )
        pv = PromptRegistry._to_domain(model)
        assert pv.prompt_name == "fin_sys"
        assert pv.version == 2
        assert pv.template == "Extract {metric}"
        assert pv.variables == ("metric",)
        assert pv.active is False
        assert pv.created_at == _NOW
