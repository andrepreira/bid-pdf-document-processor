"""Main pipeline orchestrator."""
import time
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from src.pipeline.classifier import DocumentClassifier, DocumentType

logger = structlog.get_logger()


class Pipeline:
    """Main ETL pipeline orchestrator."""
    
    def __init__(self, source_dir: str | Path):
        """Initialize pipeline.
        
        Args:
            source_dir: Directory containing PDF files
        """
        self.source_dir = Path(source_dir)
        self.results = []
        
        if not self.source_dir.exists():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")
    
    def discover_pdfs(self, pattern: str = "**/*.pdf") -> List[Path]:
        """Discover all PDF files in source directory.
        
        Args:
            pattern: Glob pattern for finding PDFs
            
        Returns:
            List of PDF file paths
        """
        pdf_files = list(self.source_dir.glob(pattern))
        logger.info(f"Discovered {len(pdf_files)} PDF files")
        return pdf_files
    
    def process_file(self, pdf_path: Path) -> Dict:
        """Process a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        
        logger.info("Processing file", file=pdf_path.name)
        
        try:
            # Classify document type
            classifier = DocumentClassifier(pdf_path)
            doc_type = classifier.classify()
            
            logger.info("Document classified", 
                       file=pdf_path.name, 
                       type=doc_type.value)
            
            # Get appropriate extractor
            extractor_class = DocumentClassifier.get_extractor_class(doc_type)
            
            if extractor_class is None:
                logger.warning("No extractor for document type", 
                             file=pdf_path.name,
                             type=doc_type.value)
                return {
                    "file_path": str(pdf_path),
                    "document_type": doc_type.value,
                    "status": "skipped",
                    "error": "No extractor available for this document type",
                }
            
            # Extract data
            extractor = extractor_class(pdf_path)
            result = extractor.run_extraction()
            
            # Add document type to result
            result["document_type"] = doc_type.value
            result["file_path"] = str(pdf_path)
            
            processing_time = time.time() - start_time
            logger.info("File processed successfully",
                       file=pdf_path.name,
                       status=result["status"],
                       processing_time=f"{processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Failed to process file",
                        file=pdf_path.name,
                        error=str(e),
                        processing_time=f"{processing_time:.2f}s")
            
            return {
                "file_path": str(pdf_path),
                "document_type": "unknown",
                "status": "failed",
                "error": str(e),
                "processing_time": processing_time,
            }
    
    def process_directory(self, pattern: str = "**/*.pdf") -> List[Dict]:
        """Process all PDFs in directory.
        
        Args:
            pattern: Glob pattern for finding PDFs
            
        Returns:
            List of extraction results
        """
        pdf_files = self.discover_pdfs(pattern)
        
        results = []
        for pdf_path in pdf_files:
            result = self.process_file(pdf_path)
            results.append(result)
        
        self.results = results
        
        # Log summary
        successful = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        
        logger.info("Pipeline completed",
                   total=len(results),
                   successful=successful,
                   failed=failed,
                   skipped=skipped)
        
        return results
    
    def get_summary(self) -> Dict:
        """Get pipeline execution summary.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get("status") == "success")
        failed = sum(1 for r in self.results if r.get("status") == "failed")
        skipped = sum(1 for r in self.results if r.get("status") == "skipped")
        
        # Group by document type
        by_type = {}
        for result in self.results:
            doc_type = result.get("document_type", "unknown")
            if doc_type not in by_type:
                by_type[doc_type] = {"total": 0, "successful": 0, "failed": 0}
            by_type[doc_type]["total"] += 1
            if result.get("status") == "success":
                by_type[doc_type]["successful"] += 1
            elif result.get("status") == "failed":
                by_type[doc_type]["failed"] += 1
        
        return {
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%",
            "by_document_type": by_type,
        }
