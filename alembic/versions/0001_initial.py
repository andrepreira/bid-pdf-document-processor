"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-20 00:00:00
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS contracts (
            id SERIAL PRIMARY KEY,
            contract_number VARCHAR(50) UNIQUE NOT NULL,
            wbs_element VARCHAR(100),
            tip_number VARCHAR(50),
            federal_aid_number VARCHAR(50),
            counties TEXT,
            description TEXT,
            date_available DATE,
            completion_date DATE,
            mbe_goal DECIMAL(5,2),
            wbe_goal DECIMAL(5,2),
            combined_goal DECIMAL(5,2),
            bid_opening_date TIMESTAMP,
            proposal_length DECIMAL(10,3),
            type_of_work VARCHAR(255),
            location TEXT,
            estimated_cost DECIMAL(15,2),
            awarded_amount DECIMAL(15,2),
            awarded_to VARCHAR(255),
            award_date DATE,
            source_file_path TEXT,
            source_file_hash VARCHAR(64),
            source_file_mtime TIMESTAMP,
            extraction_run_id VARCHAR(64),
            extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bidders (
            id SERIAL PRIMARY KEY,
            contract_id INTEGER REFERENCES contracts(id) ON DELETE CASCADE,
            bidder_name VARCHAR(255) NOT NULL,
            bidder_location VARCHAR(255),
            total_bid_amount DECIMAL(15,2),
            bid_rank INTEGER,
            percentage_diff DECIMAL(6,2),
            is_winner BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bid_items (
            id SERIAL PRIMARY KEY,
            contract_id INTEGER REFERENCES contracts(id) ON DELETE CASCADE,
            item_number VARCHAR(50),
            item_code VARCHAR(50),
            description TEXT,
            quantity DECIMAL(15,3),
            unit VARCHAR(50),
            unit_price DECIMAL(12,2),
            total_price DECIMAL(15,2),
            bidder_name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS extraction_logs (
            id SERIAL PRIMARY KEY,
            file_path TEXT NOT NULL,
            document_type VARCHAR(50),
            extraction_method VARCHAR(50),
            status VARCHAR(20) CHECK (status IN ('success', 'partial', 'failed')),
            error_message TEXT,
            confidence_score DECIMAL(4,3),
            processing_time_seconds DECIMAL(8,3),
            records_extracted INTEGER,
            needs_ocr BOOLEAN DEFAULT FALSE,
            needs_ocr_reasons TEXT,
            ocr_applied BOOLEAN DEFAULT FALSE,
            ocr_method VARCHAR(50),
            ocr_duration_seconds DECIMAL(8,3),
            file_hash VARCHAR(64),
            file_size_bytes INTEGER,
            file_mtime TIMESTAMP,
            run_id VARCHAR(64),
            extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_contracts_number ON contracts(contract_number);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_contracts_date ON contracts(bid_opening_date);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bidders_contract ON bidders(contract_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bid_items_contract ON bid_items(contract_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_extraction_logs_file ON extraction_logs(file_path);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_extraction_logs_hash ON extraction_logs(file_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_extraction_logs_status ON extraction_logs(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_extraction_logs_run ON extraction_logs(run_id);")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    op.execute("DROP TRIGGER IF EXISTS update_contracts_updated_at ON contracts;")
    op.execute(
        """
        CREATE TRIGGER update_contracts_updated_at
        BEFORE UPDATE ON contracts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS source_file_hash VARCHAR(64);")
    op.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS source_file_mtime TIMESTAMP;")
    op.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS extraction_run_id VARCHAR(64);")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS needs_ocr BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS needs_ocr_reasons TEXT;")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS ocr_applied BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS ocr_method VARCHAR(50);")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS ocr_duration_seconds DECIMAL(8,3);")
    op.execute("ALTER TABLE extraction_logs ADD COLUMN IF NOT EXISTS run_id VARCHAR(64);")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_contracts_updated_at ON contracts;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    op.execute("DROP TABLE IF EXISTS extraction_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS bid_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS bidders CASCADE;")
    op.execute("DROP TABLE IF EXISTS contracts CASCADE;")
