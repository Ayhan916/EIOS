"""PromptRegistry — load and render versioned prompt templates (ADR-011).

Prompts are stored in the `prompt_versions` table. Deploying a new prompt
is a DB operation (INSERT), not a code deployment.

Every LLM call should log the `prompt_name` + `version` in the audit trail
so the exact prompt used can be reproduced for any historical inference.

Usage:
    registry = PromptRegistry(session)
    pv = await registry.get_active("financial_extraction_system")
    if pv:
        rendered = registry.render(pv, {"company": "BMW AG", "year": "2024"})
    else:
        rendered = FALLBACK_PROMPT  # code-level default
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.prompt_version import PromptVersion
from infrastructure.persistence.models.prompt_version import PromptVersionModel


class PromptRegistry:
    """Load active prompt versions from the database.

    Each method returns None when no matching row exists — callers fall back
    to their hardcoded defaults so no prompt is silently lost during migration.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, prompt_name: str) -> PromptVersion | None:
        """Return the currently active version for this prompt name, or None."""
        stmt = (
            select(PromptVersionModel)
            .where(
                PromptVersionModel.prompt_name == prompt_name,
                PromptVersionModel.active.is_(True),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get(self, prompt_name: str, version: int) -> PromptVersion | None:
        """Return a specific version, or None if it does not exist."""
        stmt = select(PromptVersionModel).where(
            PromptVersionModel.prompt_name == prompt_name,
            PromptVersionModel.version == version,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    def render(self, prompt_version: PromptVersion, variables: dict[str, str]) -> str:
        """Render the prompt template by substituting `{variable}` placeholders.

        Args:
            prompt_version: The loaded PromptVersion to render.
            variables:      Key-value pairs for placeholder substitution.

        Returns:
            Rendered prompt string.

        Raises:
            KeyError: If a declared variable is missing from `variables`.
        """
        missing = [v for v in prompt_version.variables if v not in variables]
        if missing:
            raise KeyError(
                f"Missing variables for prompt '{prompt_version.prompt_name}' "
                f"v{prompt_version.version}: {missing}"
            )
        return prompt_version.template.format_map(variables)

    @staticmethod
    def _to_domain(model: PromptVersionModel) -> PromptVersion:
        return PromptVersion(
            prompt_name=model.prompt_name,
            version=model.version,
            template=model.template,
            variables=tuple(model.variables or []),
            active=model.active,
            created_at=model.created_at,
        )
