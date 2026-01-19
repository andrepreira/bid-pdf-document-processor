"""Pydantic models for data validation."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ContractData(BaseModel):
    """Contract data validation model."""
    
    contract_number: str = Field(..., min_length=1)
    wbs_element: Optional[str] = None
    tip_number: Optional[str] = None
    federal_aid_number: Optional[str] = None
    counties: Optional[str] = None
    description: Optional[str] = None
    date_available: Optional[date] = None
    completion_date: Optional[date] = None
    mbe_goal: Optional[Decimal] = None
    wbe_goal: Optional[Decimal] = None
    combined_goal: Optional[Decimal] = None
    bid_opening_date: Optional[datetime] = None
    proposal_length: Optional[Decimal] = None
    type_of_work: Optional[str] = None
    location: Optional[str] = None
    estimated_cost: Optional[Decimal] = None
    awarded_amount: Optional[Decimal] = None
    awarded_to: Optional[str] = None
    award_date: Optional[date] = None
    source_file_path: str
    
    @field_validator('contract_number')
    def validate_contract_number(cls, v):
        """Ensure contract number follows expected pattern."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Contract number cannot be empty")
        return v.strip().upper()


class BidderData(BaseModel):
    """Bidder data validation model."""
    
    contract_number: str
    bidder_name: str = Field(..., min_length=1)
    bidder_location: Optional[str] = None
    total_bid_amount: Optional[Decimal] = None
    bid_rank: Optional[int] = None
    percentage_diff: Optional[Decimal] = None
    is_winner: bool = False
    
    @field_validator('total_bid_amount')
    def validate_amount(cls, v):
        """Ensure bid amount is positive."""
        if v is not None and v < 0:
            raise ValueError("Bid amount must be positive")
        return v


class BidItemData(BaseModel):
    """Bid item data validation model."""
    
    contract_number: str
    item_number: Optional[str] = None
    item_code: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    bidder_name: Optional[str] = None


class ExtractedData(BaseModel):
    """Complete extracted data from a set of documents."""
    
    contract: ContractData
    bidders: List[BidderData] = []
    bid_items: List[BidItemData] = []
    extraction_metadata: dict = {}


class ExtractionResult(BaseModel):
    """Result of an extraction operation."""
    
    file_path: str
    document_type: str
    extraction_method: str
    status: str  # success, partial, failed
    error_message: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    processing_time: Optional[float] = None
    data: Optional[ExtractedData] = None
