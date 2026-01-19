"""Extractor for Award Letter documents."""
import re
from datetime import datetime
from typing import Dict, Optional

from .base_extractor import BaseExtractor


class AwardLetterExtractor(BaseExtractor):
    """Extract data from Award Letter PDFs."""
    
    def extract(self) -> Dict:
        """Extract structured data from Award Letter.
        
        Returns:
            Dictionary with award information
        """
        text = self.extract_text()
        
        data = {
            "contract_number": self._extract_contract_number(text),
            "awarded_to": self._extract_awarded_company(text),
            "awarded_amount": self._extract_awarded_amount(text),
            "award_date": self._extract_award_date(text),
            "wbs_element": self._extract_wbs_element(text),
            "counties": self._extract_counties(text),
            "description": self._extract_description(text),
        }
        
        return data
    
    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number."""
        patterns = [
            r'Contract No\.?\s*:?\s*(DA\d{5})',
            r'(DA\d{5})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_awarded_company(self, text: str) -> Optional[str]:
        """Extract the company that won the award."""
        # Look for company name at the top of the letter
        patterns = [
            r'(?:NOTIFICATION OF AWARD|Award Letter).*?\n\n.*?\n\n(.*?)(?:\n)',
            r'pleased to inform you that\s+(.*?)\s+has been awarded',
            r'Dear\s+Sir/\s*Madam:.*?inform you that\s+(.*?)\s+has been awarded',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                company = match.group(1).strip()
                # Clean up company name
                company = re.sub(r'\n', ' ', company)
                company = re.sub(r'\s+', ' ', company)
                # Take only the company name line (first line usually)
                company = company.split('\n')[0] if '\n' in company else company
                # Remove address-like parts
                if 'P.O. Box' in company or 'PO Box' in company:
                    company = company.split('P.O.')[0].split('PO')[0]
                return company.strip()
        return None
    
    def _extract_awarded_amount(self, text: str) -> Optional[float]:
        """Extract the awarded contract amount."""
        patterns = [
            r'in the amount of\s+\$\s*([\d,]+\.?\d*)',
            r'amount of\s+\$\s*([\d,]+\.?\d*)',
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
    
    def _extract_award_date(self, text: str) -> Optional[str]:
        """Extract award/letter date."""
        # Look for date at the top of the letter
        patterns = [
            r'NOTIFICATION OF AWARD\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'Award Letter\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'^([A-Za-z]+\s+\d{1,2},?\s+\d{4})',  # Date at start
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                return self._parse_date(match.group(1))
        return None
    
    def _extract_wbs_element(self, text: str) -> Optional[str]:
        """Extract WBS Element."""
        patterns = [
            r'WBS\s+Element:\s+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_counties(self, text: str) -> Optional[str]:
        """Extract county information."""
        patterns = [
            r'County:\s+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract project description."""
        patterns = [
            r'Description:\s+([^\n]+(?:\n[^\n]+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                desc = re.sub(r'\s+', ' ', desc)
                return desc[:500]
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        date_str = date_str.replace(',', '').strip()
        
        formats = [
            "%B %d %Y",
            "%b %d %Y",
            "%m/%d/%Y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
