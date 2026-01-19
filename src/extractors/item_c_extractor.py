"""Extractor for Item C Report documents."""
import re
from typing import Dict, List, Optional

from .base_extractor import BaseExtractor


class ItemCExtractor(BaseExtractor):
    """Extract data from Item C Report PDFs."""
    
    def extract(self) -> Dict:
        """Extract structured data from Item C Report.
        
        Returns:
            Dictionary with contract and bidder comparison data
        """
        text = self.extract_text()
        
        data = {
            "contract_number": self._extract_contract_number(text),
            "proposal_length": self._extract_proposal_length(text),
            "type_of_work": self._extract_type_of_work(text),
            "location": self._extract_location(text),
            "estimated_cost": self._extract_estimated_cost(text),
            "date_available": self._extract_date_available(text),
            "completion_date": self._extract_completion_date(text),
            "bidders": self._extract_bidders(text),
        }
        
        return data
    
    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number."""
        patterns = [
            r'^(DA\d{5})',
            r'(DA\d{5})',
            r'(\d{8})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1)
        return None
    
    def _extract_proposal_length(self, text: str) -> Optional[float]:
        """Extract proposal length in miles."""
        patterns = [
            r'PROPOSAL LENGTH\s+([\d.]+)\s+MILES',
            r'([\d.]+)\s+MILES',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return None
    
    def _extract_type_of_work(self, text: str) -> Optional[str]:
        """Extract type of work."""
        patterns = [
            r'TYPE OF WORK\s+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location/description."""
        patterns = [
            r'LOCATION\s+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_estimated_cost(self, text: str) -> Optional[float]:
        """Extract estimated cost."""
        patterns = [
            r'ESTIMATE\s+([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    pass
        return None
    
    def _extract_date_available(self, text: str) -> Optional[str]:
        """Extract date available."""
        patterns = [
            r'DATE AVAILABLE\s+([A-Z]{3}\s+\d{2}\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_date(match.group(1))
        return None
    
    def _extract_completion_date(self, text: str) -> Optional[str]:
        """Extract final completion date."""
        patterns = [
            r'FINAL COMPLETION\s+([A-Z]{3}\s+\d{2}\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_date(match.group(1))
        return None
    
    def _extract_bidders(self, text: str) -> List[Dict]:
        """Extract bidder comparison data."""
        bidders = []
        
        # Look for pattern like:
        # STEVENS TOWING CO INC  YONGES ISLAND, SC 2,220,630.54 -15.9
        pattern = r'([A-Z][A-Z\s&]+(?:INC|LLC|CO)?)\s+([A-Z\s,]+)\s+([\d,]+\.?\d*)\s+([-+]?\d+\.?\d*)'
        
        matches = re.finditer(pattern, text)
        
        for idx, match in enumerate(matches, 1):
            bidder_name = match.group(1).strip()
            location = match.group(2).strip()
            amount_str = match.group(3).replace(',', '')
            percent_str = match.group(4)
            
            try:
                amount = float(amount_str)
                percent_diff = float(percent_str)
                
                bidders.append({
                    "bidder_name": bidder_name,
                    "bidder_location": location,
                    "total_bid_amount": amount,
                    "percentage_diff": percent_diff,
                    "bid_rank": idx,
                })
            except ValueError:
                continue
        
        return bidders
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        from datetime import datetime
        
        date_str = date_str.strip()
        
        formats = [
            "%b %d %Y",
            "%B %d %Y",
            "%m/%d/%Y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
