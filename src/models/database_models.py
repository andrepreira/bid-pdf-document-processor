"""Database models using SQLAlchemy ORM."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Contract(Base):
    """Main contract entity."""
    
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True)
    contract_number = Column(String(50), unique=True, nullable=False)
    wbs_element = Column(String(100))
    tip_number = Column(String(50))
    federal_aid_number = Column(String(50))
    counties = Column(Text)
    description = Column(Text)
    date_available = Column(DateTime)
    completion_date = Column(DateTime)
    mbe_goal = Column(Numeric(5, 2))
    wbe_goal = Column(Numeric(5, 2))
    combined_goal = Column(Numeric(5, 2))
    bid_opening_date = Column(DateTime)
    proposal_length = Column(Numeric(10, 3))
    type_of_work = Column(String(255))
    location = Column(Text)
    estimated_cost = Column(Numeric(15, 2))
    awarded_amount = Column(Numeric(15, 2))
    awarded_to = Column(String(255))
    award_date = Column(DateTime)
    source_file_path = Column(Text)
    extraction_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bidders = relationship("Bidder", back_populates="contract", cascade="all, delete-orphan")
    bid_items = relationship("BidItem", back_populates="contract", cascade="all, delete-orphan")


class Bidder(Base):
    """Bidder information for each contract."""
    
    __tablename__ = "bidders"
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"))
    bidder_name = Column(String(255), nullable=False)
    bidder_location = Column(String(255))
    total_bid_amount = Column(Numeric(15, 2))
    bid_rank = Column(Integer)
    percentage_diff = Column(Numeric(6, 2))
    is_winner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="bidders")


class BidItem(Base):
    """Line items from bid tabs."""
    
    __tablename__ = "bid_items"
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"))
    item_number = Column(String(50))
    item_code = Column(String(50))
    description = Column(Text)
    quantity = Column(Numeric(15, 3))
    unit = Column(String(50))
    unit_price = Column(Numeric(12, 2))
    total_price = Column(Numeric(15, 2))
    bidder_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="bid_items")


class ExtractionLog(Base):
    """Log extraction pipeline execution."""
    
    __tablename__ = "extraction_logs"
    
    id = Column(Integer, primary_key=True)
    file_path = Column(Text, nullable=False)
    document_type = Column(String(50))
    extraction_method = Column(String(50))
    status = Column(String(20))  # success, partial, failed
    error_message = Column(Text)
    confidence_score = Column(Numeric(4, 3))
    processing_time_seconds = Column(Numeric(8, 3))
    records_extracted = Column(Integer)
    needs_ocr = Column(Boolean, default=False)
    needs_ocr_reasons = Column(Text)
    file_hash = Column(String(64))
    file_size_bytes = Column(Integer)
    file_mtime = Column(DateTime)
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)


def get_engine(database_url: str):
    """Create database engine."""
    return create_engine(database_url, echo=False)


def get_session(engine):
    """Create database session."""
    Session = sessionmaker(bind=engine)
    return Session()
