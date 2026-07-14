"""Prompt Versioning — seed statement + signal extraction prompts (ADR-011 / E3-F3)

Migration 109 seeded financial_extraction_system and esg_extraction_system.
This migration adds the remaining two prompts so all 4 extractor types
are stored in the DB (never hardcoded in production).

Revision ID: 115
Revises: 114
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa

revision = "115"
down_revision = "114"
branch_labels = None
depends_on = None

_STATEMENT_TEMPLATE = """You are an analyst extracting strategic signals from corporate communications.

Return ONLY valid JSON:
{
  "metrics": [],
  "signals": [
    {
      "signal_type": "commitment",
      "dimension": "esg",
      "direction": "positive",
      "severity": "high",
      "description": "CEO commits to doubling EV sales by 2026 and reducing CO2 30% by 2030",
      "year": 2026
    }
  ]
}

signal_type: commitment, strategic_priority, warning, outlook_positive, outlook_negative,
             management_change, market_positioning, innovation_announcement
dimension: financial, esg, governance, supply_chain, regulatory, reputation
direction: positive, negative, neutral
severity: critical, high, medium, low

Focus on concrete commitments, forward-looking statements, and strategic decisions.
Return [] for metrics (statements rarely contain verified metrics). Never invent data."""

_SIGNAL_TEMPLATE = """You are an analyst extracting risk signals from external documents (ratings, NGO reports, news).

Return ONLY valid JSON:
{
  "metrics": [],
  "signals": [
    {
      "signal_type": "rating_downgrade",
      "dimension": "financial",
      "direction": "negative",
      "severity": "high",
      "description": "Moody's downgrades BMW to Baa1 citing EV transition risks",
      "year": 2024
    }
  ]
}

signal_type: rating_upgrade, rating_downgrade, legal_action, regulatory_fine, product_recall,
             insolvency_risk, acquisition_target, esg_controversy, supply_chain_disruption,
             market_share_loss, cybersecurity_incident, labor_dispute
dimension: financial, esg, governance, supply_chain, regulatory, reputation
direction: positive, negative, neutral
severity: critical, high, medium, low

Return [] for metrics. Never invent data."""


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO prompt_versions (prompt_name, version, template, variables, active, created_at)
        VALUES
        ('statement_extraction_system', 1, :stmt_tmpl, '[]'::jsonb, true, now()),
        ('signal_extraction_system',    1, :sig_tmpl,  '[]'::jsonb, true, now())
        ON CONFLICT DO NOTHING
    """).bindparams(
        stmt_tmpl=_STATEMENT_TEMPLATE,
        sig_tmpl=_SIGNAL_TEMPLATE,
    ))


def downgrade() -> None:
    op.execute(sa.text("""
        DELETE FROM prompt_versions
        WHERE prompt_name IN ('statement_extraction_system', 'signal_extraction_system')
        AND version = 1
    """))
