"""Extractor for Bid Tabs documents."""
import re
from typing import Dict, List, Optional

import pdfplumber

from .base_extractor import BaseExtractor


class BidTabsExtractor(BaseExtractor):
    """Extract data from Bid Tabs PDFs (tabular data with bids)."""
    
    def extract(self) -> Dict:
        """Extract structured data from Bid Tabs.
        
        Returns:
            Dictionary with bidders and bid items
        """
        # Try table extraction first (best for structured data)
        try:
            data = self._extract_with_pdfplumber()
            if data and (data.get("bidders") or data.get("bid_items")):
                return data
        except Exception as e:
            print(f"PDFPlumber extraction failed: {e}")
        
        # Fallback to text-based extraction
        return self._extract_with_regex()
    
    def _extract_with_pdfplumber(self) -> Dict:
        """Use pdfplumber to extract tables."""
        bidders = []
        bid_items = []
        contract_number = None
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                
                # Extract contract number from text
                if not contract_number:
                    contract_number = self._extract_contract_number(text)
                
                # Extract tables
                tables = page.extract_tables()
                
                for table in tables:
                    if not table:
                        continue
                    
                    # Try to identify table type and parse accordingly
                    # Bid items table usually has columns like: Item #, Description, Quantity, Unit, Price
                    if self._is_bid_items_table(table):
                        items = self._parse_bid_items_table(table)
                        bid_items.extend(items)
        
        # Extract bidder summary and bid items from text
        text = self.extract_text()
        bidders = self._extract_bidders_from_text(text)
        if not bid_items:
            bid_items = self._extract_bid_items_from_text(text)
        
        return {
            "contract_number": contract_number,
            "bidders": bidders,
            "bid_items": bid_items,
        }
    
    def _extract_with_regex(self) -> Dict:
        """Fallback text-based extraction using regex."""
        text = self.extract_text()
        
        return {
            "contract_number": self._extract_contract_number(text),
            "bidders": self._extract_bidders_from_text(text),
            "bid_items": self._extract_bid_items_from_text(text),
        }
    
    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number."""
        patterns = [
            r'(DA\d{5})',
            r'(\d{8})',  # Alternative format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _extract_bidders_from_text(self, text: str) -> List[Dict]:
        """Extract bidder information from text."""
        bidders = []
        
        # Look for patterns like:
        # RILEY PAVING INC SUPPLY, NC
        # CONTRACT TOTAL 1,387,101.46
        
        # Extract bidder names and totals
        bidder_pattern = r'([A-Z][A-Z\s&]+(?:INC|LLC|CO)?)\s+([A-Z]+,\s*[A-Z]{2})'
        total_pattern = r'(?:CONTRACT\s+)?TOTAL\s+([\d,]+\.?\d*)'
        
        bidder_matches = list(re.finditer(bidder_pattern, text))
        total_matches = list(re.finditer(total_pattern, text))
        
        # Try to match bidders with their totals
        for i, bidder_match in enumerate(bidder_matches):
            bidder_name = bidder_match.group(1).strip()
            location = bidder_match.group(2).strip()
            
            # Find corresponding total (next occurrence after bidder name)
            total_amount = None
            for total_match in total_matches:
                if total_match.start() > bidder_match.end():
                    total_str = total_match.group(1).replace(',', '')
                    try:
                        total_amount = float(total_str)
                        break
                    except ValueError:
                        pass
            
            bidders.append({
                "bidder_name": bidder_name,
                "bidder_location": location,
                "total_bid_amount": total_amount,
                "bid_rank": i + 1,
            })
        
        # Also check for ranking info like "BIDDERS IN ORDER"
        rank_section = re.search(r'BIDDERS IN ORDER.*?CONTRACT TOTAL(.*?)(?:\n\n|\Z)', text, re.DOTALL)
        if rank_section:
            lines = rank_section.group(1).strip().split('\n')
            for idx, line in enumerate(lines):
                # Parse lines like: "1,387,101.46RILEY PAVING INC 1"
                match = re.search(r'([\d,]+\.?\d*)\s*([A-Z\s&]+(?:INC|LLC)?)\s+(\d+)', line)
                if match and idx < len(bidders):
                    bidders[idx]["bid_rank"] = int(match.group(3))
        
        return bidders
    
    def _is_bid_items_table(self, table: List[List]) -> bool:
        """Check if table contains bid items."""
        if not table or len(table) < 2:
            return False
        
        # Check header row for typical column names
        header = ' '.join([str(cell).lower() for cell in table[0] if cell])
        
        keywords = ['item', 'description', 'quantity', 'unit', 'price', 'total']
        matches = sum(1 for keyword in keywords if keyword in header)
        
        return matches >= 3
    
    def _parse_bid_items_table(self, table: List[List]) -> List[Dict]:
        """Parse bid items from table."""
        items = []
        
        if len(table) < 2:
            return items
        
        # Try to identify columns
        header = table[0]
        
        # Simple heuristic: assume columns are ordered
        for row in table[1:]:
            if not row or not any(row):
                continue
            
            try:
                item = {
                    "item_number": str(row[0]) if len(row) > 0 else None,
                    "description": str(row[1]) if len(row) > 1 else None,
                    "quantity": self._parse_number(row[2]) if len(row) > 2 else None,
                    "unit": str(row[3]) if len(row) > 3 else None,
                    "unit_price": self._parse_number(row[4]) if len(row) > 4 else None,
                    "total_price": self._parse_number(row[5]) if len(row) > 5 else None,
                }
                items.append(item)
            except Exception:
                continue
        
        return items
    
    def _parse_number(self, value) -> Optional[float]:
        """Parse number from string."""
        if value is None:
            return None
        
        try:
            # Remove commas and convert
            num_str = str(value).replace(',', '').strip()
            return float(num_str)
        except (ValueError, AttributeError):
            return None

    def _extract_bid_items_from_text(self, text: str) -> List[Dict]:
        """Extract bid items from text lines when tables are not detected."""
        if not text:
            return []

        unit_tokens = {
            "LUMP SUM",
            "LS",
            "EA",
            "TON",
            "LF",
            "SY",
            "CY",
            "HR",
            "DAY",
            "MI",
            "GAL",
        }

        items: List[Dict] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            match = re.match(r"^(\d{4})\s+(\S+)\s+([\d,]+(?:\.\d+)?)\s+(.+)$", line)
            if not match:
                continue

            item_number = match.group(1)
            item_code = match.group(2)
            quantity = self._parse_number(match.group(3))
            remainder = match.group(4)

            unit = None
            prices = [self._parse_number(p) for p in re.findall(r"[\d,]+\.\d{2}", remainder)]
            prices = [p for p in prices if p is not None]

            tokens = remainder.split()
            tokens_without_prices = [t for t in tokens if not re.match(r"^[\d,]+\.\d{2}$", t)]

            # Identify unit token (prefer last occurrence)
            if tokens_without_prices:
                idx = len(tokens_without_prices) - 1
                while idx >= 0:
                    candidate = " ".join(tokens_without_prices[idx:idx + 2]).upper()
                    single = tokens_without_prices[idx].upper()
                    if candidate in unit_tokens:
                        unit = candidate.title()
                        del tokens_without_prices[idx:idx + 2]
                        break
                    if single in unit_tokens:
                        unit = single.title()
                        del tokens_without_prices[idx]
                        break
                    idx -= 1

            description = " ".join(tokens_without_prices).strip() if tokens_without_prices else None

            item = {
                "item_number": item_number,
                "item_code": item_code,
                "description": description.strip() if description else None,
                "quantity": quantity,
                "unit": unit,
                "unit_price": prices[0] if prices else None,
                "total_price": prices[1] if len(prices) > 1 else (prices[0] if prices else None),
            }
            items.append(item)

        return items
