"""Evaluation script to compare extraction with and without LLM."""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.classifier import DocumentClassifier, DocumentType
from src.extractors.invitation_extractor import InvitationToBidExtractor
from src.extractors.bid_tabs_extractor import BidTabsExtractor
from src.extractors.award_letter_extractor import AwardLetterExtractor
from src.extractors.item_c_extractor import ItemCExtractor
from src.extractors.llm_extractor import LLMExtractor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


class ExtractionEvaluator:
    """Compare traditional vs LLM extraction methods."""
    
    def __init__(self, llm_model: str = "gemini/gemini-1.5-flash"):
        """Initialize evaluator.
        
        Args:
            llm_model: LLM model to use for comparison
        """
        self.llm_model = llm_model
        self.results = []
    
    def get_traditional_extractor(self, pdf_path: Path, doc_type: DocumentType):
        """Get appropriate traditional extractor for document type.
        
        Args:
            pdf_path: Path to PDF file
            doc_type: Document type enum
            
        Returns:
            Extractor instance or None
        """
        if doc_type == DocumentType.INVITATION_TO_BID:
            return InvitationToBidExtractor(pdf_path)
        elif doc_type == DocumentType.BID_TABS:
            return BidTabsExtractor(pdf_path)
        elif doc_type == DocumentType.AWARD_LETTER:
            return AwardLetterExtractor(pdf_path)
        elif doc_type == DocumentType.ITEM_C_REPORT:
            return ItemCExtractor(pdf_path)
        return None
    
    def calculate_completeness(self, data: Dict) -> float:
        """Calculate data completeness percentage.
        
        Args:
            data: Extracted data dictionary
            
        Returns:
            Completeness score (0-1)
        """
        if not data:
            return 0.0
        
        total_fields = len(data)
        if total_fields == 0:
            return 0.0
        
        # Count non-empty fields
        filled_fields = sum(
            1 for v in data.values()
            if v is not None and v != "" and v != [] and v != {}
        )
        
        return filled_fields / total_fields
    
    def compare_extractions(self, trad_data: Dict, llm_data: Dict) -> Dict:
        """Compare traditional and LLM extraction results.
        
        Args:
            trad_data: Data from traditional extraction
            llm_data: Data from LLM extraction
            
        Returns:
            Comparison metrics
        """
        # Calculate completeness
        trad_completeness = self.calculate_completeness(trad_data)
        llm_completeness = self.calculate_completeness(llm_data)
        
        # Count matching fields (both have non-empty values)
        all_keys = set(trad_data.keys()) | set(llm_data.keys())
        matching_fields = 0
        differing_fields = 0
        
        for key in all_keys:
            trad_val = trad_data.get(key)
            llm_val = llm_data.get(key)
            
            # Both have values
            if trad_val and llm_val:
                # Simple equality check (could be more sophisticated)
                if str(trad_val).strip() == str(llm_val).strip():
                    matching_fields += 1
                else:
                    differing_fields += 1
        
        return {
            "traditional_completeness": round(trad_completeness, 3),
            "llm_completeness": round(llm_completeness, 3),
            "completeness_improvement": round(llm_completeness - trad_completeness, 3),
            "matching_fields": matching_fields,
            "differing_fields": differing_fields,
            "total_fields": len(all_keys)
        }
    
    def evaluate_file(self, pdf_path: Path) -> Dict:
        """Evaluate a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Evaluation results
        """
        logger.info("Evaluating file", file=pdf_path.name)
        
        # Classify document
        classifier = DocumentClassifier(pdf_path)
        doc_type = classifier.classify()
        
        if doc_type == DocumentType.UNKNOWN:
            logger.warning("Unknown document type, skipping", file=pdf_path.name)
            return {
                "file": str(pdf_path),
                "status": "skipped",
                "reason": "unknown_document_type"
            }
        
        result = {
            "file": pdf_path.name,
            "document_type": doc_type.value,
            "status": "evaluated"
        }
        
        # Traditional extraction
        try:
            trad_extractor = self.get_traditional_extractor(pdf_path, doc_type)
            if not trad_extractor:
                result["traditional"] = {
                    "status": "not_supported",
                    "data": {}
                }
            else:
                start_time = time.time()
                trad_result = trad_extractor.run_extraction()
                trad_time = time.time() - start_time
                
                result["traditional"] = {
                    "status": trad_result["status"],
                    "data": trad_result.get("data", {}),
                    "processing_time": round(trad_time, 3),
                    "completeness": round(
                        self.calculate_completeness(trad_result.get("data", {})), 3
                    )
                }
        except Exception as e:
            logger.error("Traditional extraction failed", error=str(e))
            result["traditional"] = {
                "status": "error",
                "error": str(e),
                "data": {}
            }
        
        # LLM extraction
        try:
            llm_extractor = LLMExtractor(pdf_path, model=self.llm_model)
            start_time = time.time()
            llm_result = llm_extractor.run_extraction()
            llm_time = time.time() - start_time
            
            result["llm"] = {
                "status": llm_result["status"],
                "data": llm_result.get("data", {}),
                "processing_time": round(llm_time, 3),
                "completeness": round(
                    self.calculate_completeness(llm_result.get("data", {})), 3
                ),
                "model": self.llm_model
            }
        except Exception as e:
            logger.error("LLM extraction failed", error=str(e))
            result["llm"] = {
                "status": "error",
                "error": str(e),
                "data": {}
            }
        
        # Compare results
        if result.get("traditional", {}).get("data") and result.get("llm", {}).get("data"):
            result["comparison"] = self.compare_extractions(
                result["traditional"]["data"],
                result["llm"]["data"]
            )
        
        return result
    
    def evaluate_directory(self, directory: Path, pattern: str = "**/*.pdf", limit: int = None) -> List[Dict]:
        """Evaluate all PDFs in a directory.
        
        Args:
            directory: Directory containing PDFs
            pattern: Glob pattern for PDF files
            limit: Maximum number of files to evaluate (None = all)
            
        Returns:
            List of evaluation results
        """
        pdf_files = list(Path(directory).glob(pattern))
        
        if limit:
            pdf_files = pdf_files[:limit]
        
        logger.info(
            "Starting evaluation",
            total_files=len(pdf_files),
            model=self.llm_model
        )
        
        results = []
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
            
            result = self.evaluate_file(pdf_path)
            results.append(result)
            
            # Print quick summary
            if result.get("comparison"):
                comp = result["comparison"]
                print(f"  Traditional: {comp['traditional_completeness']:.1%}")
                print(f"  LLM:         {comp['llm_completeness']:.1%}")
                print(f"  Improvement: {comp['completeness_improvement']:+.1%}")
        
        self.results = results
        return results
    
    def generate_summary(self) -> Dict:
        """Generate summary statistics from evaluation results.
        
        Returns:
            Summary dictionary
        """
        if not self.results:
            return {}
        
        total = len(self.results)
        evaluated = sum(1 for r in self.results if r.get("status") == "evaluated")
        
        # Traditional stats
        trad_success = sum(
            1 for r in self.results
            if r.get("traditional", {}).get("status") == "success"
        )
        trad_completeness = [
            r["traditional"]["completeness"]
            for r in self.results
            if r.get("traditional", {}).get("completeness") is not None
        ]
        
        # LLM stats
        llm_success = sum(
            1 for r in self.results
            if r.get("llm", {}).get("status") == "success"
        )
        llm_completeness = [
            r["llm"]["completeness"]
            for r in self.results
            if r.get("llm", {}).get("completeness") is not None
        ]
        
        # Comparison stats
        improvements = [
            r["comparison"]["completeness_improvement"]
            for r in self.results
            if r.get("comparison")
        ]
        
        # Processing time stats
        trad_times = [
            r["traditional"]["processing_time"]
            for r in self.results
            if r.get("traditional", {}).get("processing_time") is not None
        ]
        llm_times = [
            r["llm"]["processing_time"]
            for r in self.results
            if r.get("llm", {}).get("processing_time") is not None
        ]
        
        summary = {
            "total_files": total,
            "evaluated_files": evaluated,
            "traditional": {
                "success_count": trad_success,
                "success_rate": round(trad_success / total, 3) if total > 0 else 0,
                "avg_completeness": round(sum(trad_completeness) / len(trad_completeness), 3) if trad_completeness else 0,
                "avg_processing_time": round(sum(trad_times) / len(trad_times), 3) if trad_times else 0
            },
            "llm": {
                "success_count": llm_success,
                "success_rate": round(llm_success / total, 3) if total > 0 else 0,
                "avg_completeness": round(sum(llm_completeness) / len(llm_completeness), 3) if llm_completeness else 0,
                "avg_processing_time": round(sum(llm_times) / len(llm_times), 3) if llm_times else 0,
                "model": self.llm_model
            },
            "comparison": {
                "avg_improvement": round(sum(improvements) / len(improvements), 3) if improvements else 0,
                "files_improved": sum(1 for imp in improvements if imp > 0),
                "files_degraded": sum(1 for imp in improvements if imp < 0),
                "files_same": sum(1 for imp in improvements if imp == 0)
            }
        }
        
        return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate traditional vs LLM extraction methods"
    )
    parser.add_argument(
        "source_dir",
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "--pattern",
        default="**/*.pdf",
        help="Glob pattern for PDF files (default: **/*.pdf)"
    )
    parser.add_argument(
        "--model",
        default="gemini/gemini-1.5-flash",
        help="LLM model to use (default: gemini/gemini-1.5-flash)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of files to evaluate"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file for detailed results"
    )
    
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = ExtractionEvaluator(llm_model=args.model)
    
    # Run evaluation
    results = evaluator.evaluate_directory(
        args.source_dir,
        pattern=args.pattern,
        limit=args.limit
    )
    
    # Generate summary
    summary = evaluator.generate_summary()
    
    # Print summary
    print("\n" + "="*70)
    print("EXTRACTION EVALUATION SUMMARY")
    print("="*70)
    print(f"\nTotal files evaluated: {summary['evaluated_files']}/{summary['total_files']}")
    
    print("\n📊 TRADITIONAL EXTRACTION (Regex + PDFPlumber)")
    print(f"  Success rate:       {summary['traditional']['success_rate']:.1%}")
    print(f"  Avg completeness:   {summary['traditional']['avg_completeness']:.1%}")
    print(f"  Avg time:           {summary['traditional']['avg_processing_time']:.3f}s")
    
    print("\n🤖 LLM EXTRACTION")
    print(f"  Model:              {summary['llm']['model']}")
    print(f"  Success rate:       {summary['llm']['success_rate']:.1%}")
    print(f"  Avg completeness:   {summary['llm']['avg_completeness']:.1%}")
    print(f"  Avg time:           {summary['llm']['avg_processing_time']:.3f}s")
    
    print("\n📈 COMPARISON")
    print(f"  Avg improvement:    {summary['comparison']['avg_improvement']:+.1%}")
    print(f"  Files improved:     {summary['comparison']['files_improved']}")
    print(f"  Files degraded:     {summary['comparison']['files_degraded']}")
    print(f"  Files unchanged:    {summary['comparison']['files_same']}")
    
    # Calculate cost and speed trade-offs
    if summary['traditional']['avg_processing_time'] > 0 and summary['llm']['avg_processing_time'] > 0:
        speed_ratio = summary['llm']['avg_processing_time'] / summary['traditional']['avg_processing_time']
        print("\n💰 TRADE-OFFS")
        print(f"  LLM is {speed_ratio:.1f}x slower")
        print(f"  Traditional cost:   $0.00 per document")
        print(f"  LLM cost (est):     $0.001-0.02 per document")
        
        improvement = summary['comparison']['avg_improvement']
        if improvement > 0:
            print(f"  Improvement:        +{improvement:.1%} completeness")
            print(f"  Worth it?           {'✅ Yes' if improvement > 0.05 else '⚠️ Maybe' if improvement > 0 else '❌ No'}")
    
    print("="*70 + "\n")
    
    # Save detailed results
    if args.output:
        output_data = {
            "summary": summary,
            "results": results
        }
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        print(f"Detailed results saved to: {output_path}\n")


if __name__ == "__main__":
    main()
