"""Extractor for Invitation to Bid documents."""
import re
from datetime import datetime
from typing import Dict, Optional

from .base_extractor import BaseExtractor


class InvitationToBidExtractor(BaseExtractor):
    """Extract data from Invitation to Bid PDFs."""
    
    def extract(self) -> Dict:
        """Extract structured data from Invitation to Bid.
        
        Returns:
            Dictionary with contract information
        """
        text = self.extract_text()
        
        data = {
            "contract_number": self._extract_contract_number(text),
            "wbs_element": self._extract_wbs_element(text),
            "counties": self._extract_counties(text),
            "description": self._extract_description(text),
            "date_available": self._extract_date_available(text),
            "completion_date": self._extract_completion_date(text),
            "mbe_goal": self._extract_mbe_goal(text),
            "wbe_goal": self._extract_wbe_goal(text),
            "combined_goal": self._extract_combined_goal(text),
            "bid_opening_date": self._extract_bid_opening_date(text),
        }
        
        return data
    
    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number (e.g., DA00564)."""
        patterns = [
            r'(DA\d{5})',
            r'Contract No\.?\s*:?\s*(DA\d{5})',
            r'project in Division One:\s*\n?\s*(DA\d{5})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_wbs_element(self, text: str) -> Optional[str]:
        """Extract WBS Element."""
        patterns = [
            r'WBS Element:\s*([^\n]+)',
            r'WBS\s*Element\s*:?\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_counties(self, text: str) -> Optional[str]:
        """Extract county/counties information."""
        patterns = [
            r'in\s+([A-Za-z,\s&]+)\s+Count(?:y|ies)',
            r'County:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract project description."""
        # Try to find description after contract number
        patterns = [
            r'DA\d{5}\s*[–-]\s*([^\n]+(?:\n[^\n]+)?)',
            r'Description:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                # Clean up multi-line descriptions
                desc = re.sub(r'\s+', ' ', desc)
                return desc[:500]  # Limit length
        return None
    
    def _extract_date_available(self, text: str) -> Optional[str]:
        """Extract Date of Availability."""
        patterns = [
            r'Date of Availability[^\n]*?is\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'The Date of Availability[^\n]*?is\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_date(match.group(1))
        return None
    
    def _extract_completion_date(self, text: str) -> Optional[str]:
        """Extract Completion Date."""
        patterns = [
            r'Completion Date[^\n]*?is\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'The Completion Date[^\n]*?is\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_date(match.group(1))
        return None
    
    def _extract_mbe_goal(self, text: str) -> Optional[float]:
        """Extract Minority Business Enterprise Goal."""
        patterns = [
            r'Minority Business Enterprise Goal\s*=\s*(\d+\.?\d*)%?',
            r'MBE Goal\s*=\s*(\d+\.?\d*)%?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_wbe_goal(self, text: str) -> Optional[float]:
        """Extract Women Business Enterprise Goal."""
        patterns = [
            r'Women Business Enterprise Goal\s*=\s*(\d+\.?\d*)%?',
            r'WBE Goal\s*=\s*(\d+\.?\d*)%?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_combined_goal(self, text: str) -> Optional[float]:
        """Extract Combined MBE/WBE Goal."""
        patterns = [
            r'Combined MBE/WBE Goal\s*=\s*(\d+\.?\d*)%?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_bid_opening_date(self, text: str) -> Optional[str]:
        """Extract Bid Opening date and time."""
        patterns = [
            r'Bid Opening will be at\s+(\d{1,2}:\d{2}\s*[ap]m)\s+on\s+([A-Za-z]+day)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}:\d{2}\s*[AP]M)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 3:
                    time_str = match.group(1)
                    date_str = match.group(3)
                else:
                    time_str = match.group(1)
                    date_str = match.group(2)
                return self._parse_datetime(date_str, time_str)
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        date_str = date_str.replace(',', '').strip()
        
        formats = [
            "%B %d %Y",
            "%b %d %Y",
            "%m/%d/%Y",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
    
    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[str]:
        """Parse datetime string to ISO format."""
        date_str = date_str.replace(',', '').strip()
        time_str = time_str.strip().upper()
        
        datetime_str = f"{date_str} {time_str}"
        
        formats = [
            "%B %d %Y %I:%M %p",
            "%b %d %Y %I:%M %p",
            "%m/%d/%Y %I:%M %p",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return None
