-- Drop existing tables if they exist
DROP TABLE IF EXISTS bid_items CASCADE;
DROP TABLE IF EXISTS bidders CASCADE;
DROP TABLE IF EXISTS bids CASCADE;
DROP TABLE IF EXISTS contracts CASCADE;
DROP TABLE IF EXISTS extraction_logs CASCADE;

-- Contracts table (main entity)
CREATE TABLE contracts (
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
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bidders table (companies that submitted bids)
CREATE TABLE bidders (
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

-- Bid Items table (line items in bid tabs)
CREATE TABLE bid_items (
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

-- Extraction logs (track pipeline execution)
CREATE TABLE extraction_logs (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    document_type VARCHAR(50),
    extraction_method VARCHAR(50),
    status VARCHAR(20) CHECK (status IN ('success', 'partial', 'failed')),
    error_message TEXT,
    confidence_score DECIMAL(4,3),
    processing_time_seconds DECIMAL(8,3),
    records_extracted INTEGER,
    file_hash VARCHAR(64),
    file_size_bytes INTEGER,
    file_mtime TIMESTAMP,
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_contracts_number ON contracts(contract_number);
CREATE INDEX idx_contracts_date ON contracts(bid_opening_date);
CREATE INDEX idx_bidders_contract ON bidders(contract_id);
CREATE INDEX idx_bid_items_contract ON bid_items(contract_id);
CREATE INDEX idx_extraction_logs_file ON extraction_logs(file_path);
CREATE INDEX idx_extraction_logs_hash ON extraction_logs(file_hash);
CREATE INDEX idx_extraction_logs_status ON extraction_logs(status);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_contracts_updated_at BEFORE UPDATE ON contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
