"""PostgreSQL loader for extracted data."""
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from src.models.database_models import (
    Base,
    BidItem,
    Bidder,
    Contract,
    ExtractionLog,
    get_engine,
    get_session,
)

load_dotenv()
logger = structlog.get_logger()


class PostgresLoader:
    """Load extracted data into PostgreSQL database."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize loader.
        
        Args:
            database_url: PostgreSQL connection string. If None, uses env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not provided")
        
        self.engine = get_engine(self.database_url)
        self.session = get_session(self.engine)
    
    def create_tables(self):
        """Create database tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")
    
    def load_contract(self, data: Dict) -> Optional[Contract]:
        """Load contract data.
        
        Args:
            data: Extracted contract data
            
        Returns:
            Contract object or None if failed
        """
        try:
            contract_number = data.get('contract_number')
            if not contract_number:
                logger.warning("Contract number missing, skipping")
                return None
            
            # Check if contract already exists
            existing = self.session.query(Contract).filter_by(
                contract_number=contract_number
            ).first()
            
            if existing:
                # Update existing record
                for key, value in data.items():
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)
                contract = existing
                logger.info("Contract updated", contract_number=contract_number)
            else:
                # Create new record
                contract = Contract(**data)
                self.session.add(contract)
                logger.info("Contract created", contract_number=contract_number)
            
            self.session.commit()
            return contract
            
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to load contract",
                        contract_number=data.get('contract_number'),
                        error=str(e))
            return None
    
    def load_bidders(self, contract_id: int, bidders: List[Dict]) -> int:
        """Load bidder data for a contract.
        
        Args:
            contract_id: Contract database ID
            bidders: List of bidder dictionaries
            
        Returns:
            Number of bidders loaded
        """
        count = 0
        existing = self.session.query(Bidder).filter_by(contract_id=contract_id).all()
        existing_keys = {
            self._bidder_key(row.bidder_name, row.total_bid_amount) for row in existing
        }
        pending_keys = set()
        for bidder_data in bidders:
            try:
                bidder_data['contract_id'] = contract_id
                bidder_key = self._bidder_key(
                    bidder_data.get('bidder_name'),
                    bidder_data.get('total_bid_amount')
                )
                if bidder_key in existing_keys or bidder_key in pending_keys:
                    continue
                bidder = Bidder(**bidder_data)
                self.session.add(bidder)
                pending_keys.add(bidder_key)
                count += 1
            except Exception as e:
                logger.warning("Failed to load bidder",
                             bidder=bidder_data.get('bidder_name'),
                             error=str(e))
        
        try:
            self.session.commit()
            logger.info(f"Loaded {count} bidders", contract_id=contract_id)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to commit bidders", error=str(e))
            count = 0
        
        return count
    
    def load_bid_items(self, contract_id: int, items: List[Dict]) -> int:
        """Load bid items for a contract.
        
        Args:
            contract_id: Contract database ID
            items: List of bid item dictionaries
            
        Returns:
            Number of items loaded
        """
        count = 0
        for item_data in items:
            try:
                item_data['contract_id'] = contract_id
                item = BidItem(**item_data)
                self.session.add(item)
                count += 1
            except Exception as e:
                logger.warning("Failed to load bid item",
                             item=item_data.get('item_number'),
                             error=str(e))
        
        try:
            self.session.commit()
            logger.info(f"Loaded {count} bid items", contract_id=contract_id)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to commit bid items", error=str(e))
            count = 0
        
        return count
    
    def log_extraction(self, extraction_result: Dict) -> None:
        """Log extraction results to database.
        
        Args:
            extraction_result: Extraction result dictionary
        """
        try:
            file_mtime = extraction_result.get('metadata', {}).get('file_mtime')
            file_mtime_dt = self._parse_datetime(file_mtime) if file_mtime else None

            log_data = {
                'file_path': extraction_result.get('file_path'),
                'document_type': extraction_result.get('document_type'),
                'extraction_method': extraction_result.get('metadata', {}).get('extraction_method'),
                'status': extraction_result.get('status'),
                'error_message': extraction_result.get('error'),
                'processing_time_seconds': extraction_result.get('metadata', {}).get('processing_time'),
                'needs_ocr': extraction_result.get('metadata', {}).get('needs_ocr'),
                'needs_ocr_reasons': self._format_ocr_reasons(
                    extraction_result.get('metadata', {}).get('needs_ocr_reasons')
                ),
                'ocr_applied': extraction_result.get('metadata', {}).get('ocr_applied'),
                'ocr_method': extraction_result.get('metadata', {}).get('ocr_method'),
                'ocr_duration_seconds': extraction_result.get('metadata', {}).get('ocr_duration_seconds'),
                'file_hash': extraction_result.get('metadata', {}).get('file_hash'),
                'file_size_bytes': extraction_result.get('metadata', {}).get('file_size_bytes'),
                'file_mtime': file_mtime_dt,
                'run_id': extraction_result.get('metadata', {}).get('run_id'),
            }
            
            log = ExtractionLog(**log_data)
            self.session.add(log)
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to log extraction", error=str(e))

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from ISO string or timestamp."""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except Exception:
                return None

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return None

        return None

    def _format_ocr_reasons(self, reasons) -> Optional[str]:
        """Format OCR reasons into a string for storage."""
        if not reasons:
            return None
        if isinstance(reasons, str):
            return reasons
        if isinstance(reasons, list):
            return ",".join(str(reason) for reason in reasons)
        return str(reasons)
    
    def load_extraction_result(self, result: Dict) -> bool:
        """Load complete extraction result.
        
        Args:
            result: Full extraction result from pipeline
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Log extraction
            self.log_extraction(result)
            
            # Only process extractions with data
            if result.get('status') not in ('success', 'partial') or 'data' not in result:
                return True  # Logging is success enough for failed extractions
            
            data = result['data']
            
            # Load contract
            file_mtime = result.get('metadata', {}).get('file_mtime')
            file_mtime_dt = self._parse_datetime(file_mtime) if file_mtime else None

            contract_number = data.get('contract_number')
            if not contract_number:
                contract_number = self._infer_contract_number_from_file_path(result.get('file_path'))

            contract = self.load_contract({
                'contract_number': self._normalize_contract_number(contract_number),
                'wbs_element': data.get('wbs_element'),
                'counties': data.get('counties'),
                'description': data.get('description'),
                'date_available': self._parse_date(data.get('date_available')),
                'completion_date': self._parse_date(data.get('completion_date')),
                'mbe_goal': data.get('mbe_goal'),
                'wbe_goal': data.get('wbe_goal'),
                'combined_goal': data.get('combined_goal'),
                'bid_opening_date': self._parse_datetime(data.get('bid_opening_date')),
                'proposal_length': data.get('proposal_length'),
                'type_of_work': data.get('type_of_work'),
                'location': data.get('location'),
                'estimated_cost': data.get('estimated_cost'),
                'awarded_amount': data.get('awarded_amount'),
                'awarded_to': data.get('awarded_to'),
                'award_date': self._parse_date(data.get('award_date')),
                'source_file_path': result.get('file_path'),
                'source_file_hash': result.get('metadata', {}).get('file_hash'),
                'source_file_mtime': file_mtime_dt,
                'extraction_run_id': result.get('metadata', {}).get('run_id'),
            })
            
            if not contract:
                return False
            
            # Load bidders if present
            if 'bidders' in data and data['bidders']:
                self.load_bidders(contract.id, data['bidders'])
            
            # Load bid items if present
            if 'bid_items' in data and data['bid_items']:
                self.load_bid_items(contract.id, data['bid_items'])
            
            return True
            
        except Exception as e:
            logger.error("Failed to load extraction result",
                        file=result.get('file_path'),
                        error=str(e))
            return False
    
    def load_batch(self, results: List[Dict]) -> Dict:
        """Load batch of extraction results.
        
        Args:
            results: List of extraction results
            
        Returns:
            Summary dictionary with statistics
        """
        total = len(results)
        successful = 0
        failed = 0
        
        for result in results:
            if self.load_extraction_result(result):
                successful += 1
            else:
                failed += 1
        
        summary = {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/total*100):.1f}%" if total > 0 else "0%"
        }
        
        logger.info("Batch loading completed", **summary)
        return summary
    
    def _parse_date(self, date_str: Optional[str]):
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            if isinstance(date_str, datetime):
                return date_str
            return datetime.fromisoformat(date_str)
        except Exception:
            return None
    
    def _parse_datetime(self, datetime_str: Optional[str]):
        """Parse datetime string to datetime object."""
        return self._parse_date(datetime_str)

    def _normalize_contract_number(self, value: Optional[str]) -> Optional[str]:
        """Normalize contract numbers for consistent keys."""
        if not value:
            return None
        return str(value).strip().upper()

    def _infer_contract_number_from_file_path(self, file_path: Optional[str]) -> Optional[str]:
        """Infer contract number from file path when missing."""
        if not file_path:
            return None

        import re

        filename = Path(file_path).name
        patterns = [
            r"(DA\d{5})",
            r"\b(\d{8})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def _bidder_key(self, name, total_amount) -> str:
        """Build a deduplication key for bidders."""
        name_key = (name or "").strip().upper()
        amount_key = str(total_amount) if total_amount is not None else ""
        return f"{name_key}|{amount_key}"
    
    def close(self):
        """Close database connection."""
        self.session.close()
        logger.info("Database connection closed")
