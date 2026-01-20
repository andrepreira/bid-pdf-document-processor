"""Extractor for Bids As Read documents."""
import re
from typing import Dict, List, Optional

import fitz
import pdfplumber

from .base_extractor import BaseExtractor


class BidsAsReadExtractor(BaseExtractor):
    """Extract data from Bids As Read PDFs."""

    def extract(self) -> Dict:
        """Extract structured data from Bids As Read.

        Returns:
            Dictionary with contract number and bidders
        """
        text = self._extract_text_any()

        contract_number = self._extract_contract_number(text)
        bidders = self._extract_bidders(text)

        return {
            "contract_number": contract_number,
            "bidders": bidders,
            "bid_items": [],
        }

    def _extract_text_any(self) -> str:
        """Try multiple text extraction strategies."""
        text = ""
        try:
            text = self.extract_text() or ""
        except Exception:
            text = ""

        if text.strip():
            return text

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                parts = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(parts)
        except Exception:
            text = ""

        if text.strip():
            return text

        try:
            doc = fitz.open(self.pdf_path)
            parts = [page.get_text() or "" for page in doc]
            text = "\n".join(parts)
        except Exception:
            text = ""

        return text

    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number from text or filename."""
        patterns = [
            r"(DA\d{5})",
            r"\b(\d{8})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        filename = self.pdf_name.upper()
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1).upper()

        return None

    def _extract_bidders(self, text: str) -> List[Dict]:
        """Extract bidder names and amounts from text."""
        bidders: List[Dict] = []
        if not text:
            return bidders

        lines = [self._normalize_line(line) for line in text.splitlines()]

        patterns = [
            re.compile(
                r"^(?P<bidder>[A-Z][A-Z0-9&.,'\- ]{3,})\s+"
                r"(?P<location>[A-Z][A-Z .\-]+,\s*[A-Z]{2})\s+"
                r"(?P<amount>[\d,]+\.\d{2})(?:\s+(?P<rank>\d+))?$"
            ),
            re.compile(
                r"^(?P<amount>[\d,]+\.\d{2})\s+"
                r"(?P<bidder>[A-Z][A-Z0-9&.,'\- ]{3,})"
                r"(?:\s+(?P<location>[A-Z][A-Z .\-]+,\s*[A-Z]{2}))?$"
            ),
        ]

        for line in lines:
            if not line:
                continue
            if self._is_header_line(line):
                continue

            for pattern in patterns:
                match = pattern.match(line)
                if not match:
                    continue

                bidder_name = (match.group("bidder") or "").strip()
                if not bidder_name or not re.search(r"[A-Z]", bidder_name):
                    continue

                amount = self._parse_amount(match.group("amount"))
                if amount is None:
                    continue

                location = (match.groupdict().get("location") or "").strip() or None
                rank = self._parse_int(match.groupdict().get("rank"))
                percent_diff = self._parse_percent(line)

                bidders.append({
                    "bidder_name": bidder_name,
                    "bidder_location": location,
                    "total_bid_amount": amount,
                    "bid_rank": rank,
                    "percentage_diff": percent_diff,
                })
                break

        for idx, bidder in enumerate(bidders, 1):
            if bidder.get("bid_rank") is None:
                bidder["bid_rank"] = idx

        return bidders

    def _normalize_line(self, line: str) -> str:
        """Normalize whitespace in a line."""
        return re.sub(r"\s+", " ", line).strip()

    def _is_header_line(self, line: str) -> bool:
        """Identify header or non-data lines."""
        header_keywords = [
            "BIDS AS READ",
            "BID SUMMARY",
            "CONTRACT",
            "TOTAL",
            "ENGINEER",
            "BIDDER",
            "BIDDERS",
        ]
        return any(keyword in line for keyword in header_keywords)

    def _parse_amount(self, value: Optional[str]) -> Optional[float]:
        """Parse currency amount."""
        if not value:
            return None
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse int value."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _parse_percent(self, line: str) -> Optional[float]:
        """Extract percentage value if present in line."""
        match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*%", line)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None
