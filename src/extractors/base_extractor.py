"""Base extractor interface."""
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

import pypdf
import structlog

logger = structlog.get_logger()


class BaseExtractor(ABC):
    """Base class for all PDF extractors."""
    
    def __init__(self, pdf_path: str | Path):
        """Initialize extractor with PDF path.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.pdf_name = self.pdf_path.name
        self.extraction_method = self.__class__.__name__
        self.start_time = None
        self.processing_time = None
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
    
    def extract_text(self) -> str:
        """Extract raw text from PDF using pypdf.
        
        Returns:
            Full text content of the PDF
        """
        try:
            reader = pypdf.PdfReader(str(self.pdf_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error("Failed to extract text", file=self.pdf_name, error=str(e))
            raise
    
    def extract_text_from_page(self, page_num: int) -> str:
        """Extract text from a specific page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Text content of the specified page
        """
        try:
            reader = pypdf.PdfReader(str(self.pdf_path))
            if page_num >= len(reader.pages):
                raise ValueError(f"Page {page_num} does not exist")
            return reader.pages[page_num].extract_text()
        except Exception as e:
            logger.error("Failed to extract page", page=page_num, error=str(e))
            raise
    
    @abstractmethod
    def extract(self) -> Dict:
        """Extract structured data from PDF.
        
        This method must be implemented by subclasses.
        
        Returns:
            Dictionary containing extracted data
        """
        pass
    
    def run_extraction(self) -> Dict:
        """Run the extraction with timing and error handling.
        
        Returns:
            Dictionary with extraction results and metadata
        """
        self.start_time = time.time()
        
        try:
            logger.info(
                "Starting extraction",
                file=self.pdf_name,
                method=self.extraction_method
            )
            
            data = self.extract()
            text_stats = self._extract_text_stats()
            
            self.processing_time = time.time() - self.start_time
            
            logger.info(
                "Extraction completed",
                file=self.pdf_name,
                method=self.extraction_method,
                processing_time=f"{self.processing_time:.2f}s"
            )
            
            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "file_path": str(self.pdf_path),
                    "extraction_method": self.extraction_method,
                    "processing_time": self.processing_time,
                    **text_stats,
                }
            }
            
        except Exception as e:
            self.processing_time = time.time() - self.start_time
            logger.error(
                "Extraction failed",
                file=self.pdf_name,
                method=self.extraction_method,
                error=str(e),
                processing_time=f"{self.processing_time:.2f}s"
            )
            
            text_stats = self._extract_text_stats()
            return {
                "status": "failed",
                "data": None,
                "error": str(e),
                "metadata": {
                    "file_path": str(self.pdf_path),
                    "extraction_method": self.extraction_method,
                    "processing_time": self.processing_time,
                    **text_stats,
                }
            }
    
    def calculate_confidence_score(self, data: Dict) -> float:
        """Calculate confidence score based on completeness of extracted data.
        
        Args:
            data: Extracted data dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        if not data:
            return 0.0
        
        # Count non-null fields
        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v is not None and v != "")
        
        return filled_fields / total_fields if total_fields > 0 else 0.0

    def _extract_text_stats(self) -> Dict:
        """Compute simple text stats using pypdf.

        Returns:
            Dict with text length and pages with text.
        """
        try:
            reader = pypdf.PdfReader(str(self.pdf_path))
            text_length = 0
            pages_with_text = 0
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_with_text += 1
                    text_length += len(page_text)
            return {
                "text_length": text_length,
                "text_pages_with_content": pages_with_text,
                "text_page_count": len(reader.pages),
            }
        except Exception:
            return {
                "text_length": 0,
                "text_pages_with_content": 0,
                "text_page_count": 0,
            }
