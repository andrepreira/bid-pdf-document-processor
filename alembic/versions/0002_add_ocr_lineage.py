"""Add OCR and lineage columns.

Revision ID: 0002_add_ocr_lineage
Revises: 0001_initial
Create Date: 2026-01-20 00:00:01
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_ocr_lineage"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS source_file_hash VARCHAR(64);")
    op.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS source_file_mtime TIMESTAMP;")
    op.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS extraction_run_id VARCHAR(64);")

    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS ocr_applied BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS ocr_method VARCHAR(50);")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS ocr_duration_seconds DECIMAL(8,3);")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS run_id VARCHAR(64);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_extraction_logs_run ON extraction_logs(run_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_extraction_logs_run;")
    op.execute("ALTER TABLE extraction_logs DROP COLUMN IF EXISTS run_id;")
    op.execute("ALTER TABLE extraction_logs DROP COLUMN IF EXISTS ocr_duration_seconds;")
    op.execute("ALTER TABLE extraction_logs DROP COLUMN IF EXISTS ocr_method;")
    op.execute("ALTER TABLE extraction_logs DROP COLUMN IF EXISTS ocr_applied;")

    op.execute("ALTER TABLE contracts DROP COLUMN IF EXISTS extraction_run_id;")
    op.execute("ALTER TABLE contracts DROP COLUMN IF EXISTS source_file_mtime;")
    op.execute("ALTER TABLE contracts DROP COLUMN IF EXISTS source_file_hash;")
