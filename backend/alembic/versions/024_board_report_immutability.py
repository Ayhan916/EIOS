"""board_report_immutability

Add a PostgreSQL BEFORE UPDATE trigger that prevents modifications to the
content fields of board_reports after initial insert. This enforces the
domain invariant that board reports are immutable once generated.

Revision ID: 024
Revises: 023
Create Date: 2026-06-19
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION board_reports_immutability_check()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF (
                NEW.report_data IS DISTINCT FROM OLD.report_data OR
                NEW.supplier_snapshot IS DISTINCT FROM OLD.supplier_snapshot OR
                NEW.executive_summary IS DISTINCT FROM OLD.executive_summary
            ) THEN
                RAISE EXCEPTION
                    'board_reports.% is immutable after creation (report_id=%)',
                    CASE
                        WHEN NEW.report_data IS DISTINCT FROM OLD.report_data THEN 'report_data'
                        WHEN NEW.supplier_snapshot IS DISTINCT FROM OLD.supplier_snapshot THEN 'supplier_snapshot'
                        ELSE 'executive_summary'
                    END,
                    OLD.id
                USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER board_reports_immutability
        BEFORE UPDATE ON board_reports
        FOR EACH ROW
        EXECUTE FUNCTION board_reports_immutability_check();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS board_reports_immutability ON board_reports;")
    op.execute("DROP FUNCTION IF EXISTS board_reports_immutability_check();")
