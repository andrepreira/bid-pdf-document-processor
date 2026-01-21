"""Main pipeline orchestrator."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import structlog

from src.pipeline.classifier import DocumentClassifier, DocumentType
from src.transformers.file_mapping import MappingResolver, apply_mapping
from src.transformers.ocr import OCRProcessor

logger = structlog.get_logger()


class Pipeline:
    """Main ETL pipeline orchestrator."""
    
    def __init__(self, source_dir: str | Path, incremental: bool = False, state_file: Optional[str] = None):
        """Initialize pipeline.
        
        Args:
            source_dir: Directory containing PDF files
            incremental: Skip unchanged files using cached fingerprints
            state_file: Optional path for incremental state cache
        """
        self.source_dir = Path(source_dir)
        self.results = []
        self.incremental = incremental
        self.state_file = Path(state_file) if state_file else self.source_dir / ".pipeline_state.json"
        self._state: Dict[str, Dict] = {}
        self.mapping_resolver = MappingResolver(self.source_dir)
        self.ocr_processor = OCRProcessor()
        self.run_id = uuid4().hex
        
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

    def _compute_file_fingerprint(self, pdf_path: Path) -> Dict:
        """Compute a fingerprint for a file (hash, size, mtime)."""
        hasher = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)

        stat = pdf_path.stat()
        return {
            "file_hash": hasher.hexdigest(),
            "file_size_bytes": stat.st_size,
            "file_mtime": stat.st_mtime,
        }

    def _load_state(self) -> Dict[str, Dict]:
        """Load incremental processing state from disk."""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_state(self, state: Dict[str, Dict]) -> None:
        """Persist incremental processing state to disk."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save pipeline state", error=str(e))

    def _is_unchanged(self, pdf_path: Path, fingerprint: Dict) -> bool:
        """Check if file fingerprint matches cached state."""
        cached = self._state.get(str(pdf_path))
        if not cached:
            return False

        return (
            cached.get("file_hash") == fingerprint.get("file_hash")
            and cached.get("file_size_bytes") == fingerprint.get("file_size_bytes")
            and cached.get("file_mtime") == fingerprint.get("file_mtime")
        )

    def _build_skip_result(self, pdf_path: Path, fingerprint: Dict) -> Dict:
        """Build a standardized skip result for unchanged files."""
        classifier = DocumentClassifier(pdf_path)
        doc_type = classifier.classify_filename_only()
        file_mtime_iso = datetime.fromtimestamp(
            fingerprint["file_mtime"], tz=timezone.utc
        ).isoformat()

        return {
            "file_path": str(pdf_path),
            "document_type": doc_type.value,
            "status": "skipped",
            "error": "unchanged",
            "metadata": {
                "file_hash": fingerprint.get("file_hash"),
                "file_size_bytes": fingerprint.get("file_size_bytes"),
                "file_mtime": file_mtime_iso,
                "file_mtime_ts": fingerprint.get("file_mtime"),
                "skip_reason": "unchanged",
            },
        }
    
    def process_file(self, pdf_path: Path, fingerprint: Optional[Dict] = None) -> Dict:
        """Process a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        fingerprint = fingerprint or self._compute_file_fingerprint(pdf_path)
        
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
            
            result = self._run_extraction(
                extractor_class=extractor_class,
                pdf_path=pdf_path,
                doc_type=doc_type,
                file_name_for_mapping=pdf_path.name,
                result_file_path=pdf_path,
            )

            self._normalize_contract_number(result, pdf_path)

            needs_ocr, reasons = self._assess_needs_ocr(result)
            if needs_ocr:
                result = self._attempt_ocr_and_reextract(
                    extractor_class=extractor_class,
                    original_pdf_path=pdf_path,
                    doc_type=doc_type,
                    file_name_for_mapping=pdf_path.name,
                    initial_result=result,
                )

                self._normalize_contract_number(result, pdf_path)
                needs_ocr, reasons = self._assess_needs_ocr(result)

            result.setdefault("metadata", {}).update({
                "needs_ocr": needs_ocr,
                "needs_ocr_reasons": reasons,
            })
            if needs_ocr and result.get("status") == "success":
                result["status"] = "partial"
                logger.warning(
                    "OCR recommended",
                    file=pdf_path.name,
                    reasons=reasons,
                )

            partial_reasons = self._assess_partial_reasons(result)
            if partial_reasons:
                result.setdefault("metadata", {})["partial_reasons"] = partial_reasons
                if result.get("status") == "success":
                    result["status"] = "partial"
                    logger.warning(
                        "Partial extraction detected",
                        file=pdf_path.name,
                        reasons=partial_reasons,
                    )

            file_mtime_iso = datetime.fromtimestamp(
                fingerprint["file_mtime"], tz=timezone.utc
            ).isoformat()
            result.setdefault("metadata", {}).update({
                "run_id": self.run_id,
                "file_hash": fingerprint.get("file_hash"),
                "file_size_bytes": fingerprint.get("file_size_bytes"),
                "file_mtime": file_mtime_iso,
                "file_mtime_ts": fingerprint.get("file_mtime"),
            })
            
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
                "metadata": {
                    "file_hash": fingerprint.get("file_hash"),
                    "file_size_bytes": fingerprint.get("file_size_bytes"),
                    "file_mtime": datetime.fromtimestamp(
                        fingerprint["file_mtime"], tz=timezone.utc
                    ).isoformat(),
                    "file_mtime_ts": fingerprint.get("file_mtime"),
                },
            }

    def _assess_needs_ocr(self, result: Dict) -> tuple[bool, List[str]]:
        """Heuristic to detect PDFs that likely need OCR.

        Args:
            result: Extraction result dictionary

        Returns:
            Tuple of (needs_ocr, reasons)
        """
        reasons: List[str] = []
        metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
        text_length = metadata.get("text_length") or 0
        pages_with_text = metadata.get("text_pages_with_content") or 0

        if pages_with_text == 0 or text_length < 50:
            reasons.append("no_text_extracted")

        data = result.get("data") or {}
        if isinstance(data, dict):
            total_fields = len(data)
            filled_fields = 0
            for value in data.values():
                if value is None:
                    continue
                if isinstance(value, (list, dict)) and len(value) == 0:
                    continue
                if isinstance(value, str) and value.strip() == "":
                    continue
                filled_fields += 1

            if total_fields == 0 or filled_fields == 0:
                reasons.append("empty_data")
            elif filled_fields <= 1 and (data.get("bidders") == [] and data.get("bid_items") == []):
                reasons.append("low_field_coverage")

        return (len(reasons) > 0, reasons)

    def _assess_partial_reasons(self, result: Dict) -> List[str]:
        """Determine reasons to mark a result as partial."""
        reasons: List[str] = []
        data = result.get("data") if isinstance(result, dict) else None
        if isinstance(data, dict):
            if not data.get("contract_number"):
                reasons.append("missing_contract_number")

        return reasons

    def _normalize_contract_number(self, result: Dict, pdf_path: Path) -> None:
        """Populate missing contract number from filename when possible."""
        if not isinstance(result, dict):
            return
        data = result.get("data")
        if not isinstance(data, dict):
            return

        if data.get("contract_number"):
            return

        inferred = self._infer_contract_number_from_filename(pdf_path.name)
        if inferred:
            data["contract_number"] = inferred
            result.setdefault("metadata", {})["contract_number_source"] = "filename"

    def _infer_contract_number_from_filename(self, filename: str) -> Optional[str]:
        """Infer contract number from filename."""
        import re

        patterns = [
            r"(DA\d{5})",
            r"\b(\d{8})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def _run_extraction(
        self,
        extractor_class,
        pdf_path: Path,
        doc_type: DocumentType,
        file_name_for_mapping: str,
        result_file_path: Path,
    ) -> Dict:
        """Run extraction and apply mapping for a PDF path."""
        extractor = extractor_class(pdf_path)
        result = extractor.run_extraction()

        if result.get("status") == "success" and result.get("data"):
            mapping = self.mapping_resolver.resolve(doc_type.value, file_name_for_mapping)
            mapped_data, mapping_meta = apply_mapping(result["data"], mapping)
            result["data"] = mapped_data
            result.setdefault("metadata", {})["mapping"] = mapping_meta

        result["document_type"] = doc_type.value
        result["file_path"] = str(result_file_path)
        return result

    def _attempt_ocr_and_reextract(
        self,
        extractor_class,
        original_pdf_path: Path,
        doc_type: DocumentType,
        file_name_for_mapping: str,
        initial_result: Dict,
    ) -> Dict:
        """Run OCR when needed and re-run extraction using OCR output."""
        ocr_path, ocr_meta = self.ocr_processor.run(original_pdf_path)
        result = initial_result
        result.setdefault("metadata", {}).update(ocr_meta)

        if not ocr_path:
            return result

        try:
            result = self._run_extraction(
                extractor_class=extractor_class,
                pdf_path=ocr_path,
                doc_type=doc_type,
                file_name_for_mapping=file_name_for_mapping,
                result_file_path=original_pdf_path,
            )
            result.setdefault("metadata", {}).update(ocr_meta)
            result.setdefault("metadata", {})["ocr_source_file"] = str(ocr_path)
            return result
        finally:
            try:
                ocr_path.unlink(missing_ok=True)
            except Exception:
                pass
    
    def process_directory(self, pattern: str = "**/*.pdf") -> List[Dict]:
        """Process all PDFs in directory.
        
        Args:
            pattern: Glob pattern for finding PDFs
            
        Returns:
            List of extraction results
        """
        pdf_files = self.discover_pdfs(pattern)

        if self.incremental:
            self._state = self._load_state()
        
        results = []
        for pdf_path in pdf_files:
            fingerprint = self._compute_file_fingerprint(pdf_path)

            if self.incremental and self._is_unchanged(pdf_path, fingerprint):
                skip_result = self._build_skip_result(pdf_path, fingerprint)
                skip_result.setdefault("metadata", {})["run_id"] = self.run_id
                results.append(skip_result)
                continue

            result = self.process_file(pdf_path, fingerprint)
            results.append(result)

            if self.incremental and result.get("status") == "success":
                self._state[str(pdf_path)] = fingerprint
        
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

        if self.incremental:
            self._save_state(self._state)
        
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
