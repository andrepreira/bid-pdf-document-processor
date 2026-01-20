"""Document classifier to identify PDF types."""
import re
from enum import Enum
from pathlib import Path
from typing import Optional

import pypdf


class DocumentType(Enum):
    """Enum for document types."""
    INVITATION_TO_BID = "invitation_to_bid"
    BID_TABS = "bid_tabs"
    AWARD_LETTER = "award_letter"
    ITEM_C_REPORT = "item_c_report"
    BID_SUMMARY = "bid_summary"
    BIDS_AS_READ = "bids_as_read"
    UNKNOWN = "unknown"


class DocumentClassifier:
    """Classify PDF documents by type."""
    
    def __init__(self, pdf_path: str | Path):
        """Initialize classifier.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.filename = self.pdf_path.name.lower()
    
    def classify(self) -> DocumentType:
        """Classify the document type.
        
        Returns:
            DocumentType enum value
        """
        # First, try filename-based classification
        doc_type = self._classify_by_filename()
        if doc_type != DocumentType.UNKNOWN:
            return doc_type
        
        # Fall back to content-based classification
        return self._classify_by_content()

    def classify_filename_only(self) -> DocumentType:
        """Classify based on filename patterns only.

        Returns:
            DocumentType enum value
        """
        return self._classify_by_filename()
    
    def _classify_by_filename(self) -> DocumentType:
        """Classify based on filename patterns."""
        filename = self.filename
        
        if "invitation" in filename and "bid" in filename:
            return DocumentType.INVITATION_TO_BID
        
        if "bid tab" in filename or "bid_tab" in filename or "bidtab" in filename:
            return DocumentType.BID_TABS
        
        if "award" in filename and "letter" in filename:
            return DocumentType.AWARD_LETTER
        
        if "item c" in filename or "item_c" in filename or "itemc" in filename:
            return DocumentType.ITEM_C_REPORT
        
        if "bid summary" in filename or "bidsummary" in filename:
            return DocumentType.BID_SUMMARY
        
        if "bids as read" in filename or "bids_as_read" in filename:
            return DocumentType.BIDS_AS_READ
        
        return DocumentType.UNKNOWN
    
    def _classify_by_content(self) -> DocumentType:
        """Classify based on PDF content."""
        try:
            # Extract first page text
            reader = pypdf.PdfReader(str(self.pdf_path))
            if len(reader.pages) == 0:
                return DocumentType.UNKNOWN
            
            text = reader.pages[0].extract_text().lower()
            
            # Check for distinctive patterns
            if "notice to prospective bidders" in text or "invitation to bid" in text:
                return DocumentType.INVITATION_TO_BID
            
            if "notification of award" in text or "pleased to inform you that" in text:
                return DocumentType.AWARD_LETTER
            
            if "item c" in text and ("$ totals" in text or "% diff" in text):
                return DocumentType.ITEM_C_REPORT
            
            if "roadway items" in text and ("bidder" in text or "contractor" in text):
                return DocumentType.BID_TABS
            
            if "bids as read" in text:
                return DocumentType.BIDS_AS_READ
            
        except Exception:
            pass
        
        return DocumentType.UNKNOWN
    
    @staticmethod
    def get_extractor_class(doc_type: DocumentType):
        """Get the appropriate extractor class for document type.
        
        Args:
            doc_type: Document type
            
        Returns:
            Extractor class or None
        """
        from src.extractors import (
            AwardLetterExtractor,
            BidSummaryExtractor,
            BidTabsExtractor,
            BidsAsReadExtractor,
            InvitationToBidExtractor,
            ItemCExtractor,
        )
        
        mapping = {
            DocumentType.INVITATION_TO_BID: InvitationToBidExtractor,
            DocumentType.BID_TABS: BidTabsExtractor,
            DocumentType.AWARD_LETTER: AwardLetterExtractor,
            DocumentType.ITEM_C_REPORT: ItemCExtractor,
            DocumentType.BID_SUMMARY: BidSummaryExtractor,
            DocumentType.BIDS_AS_READ: BidsAsReadExtractor,
        }
        
        return mapping.get(doc_type)
