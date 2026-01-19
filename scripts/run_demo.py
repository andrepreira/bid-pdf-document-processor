"""Complete end-to-end demonstration script."""
import argparse
import json
import sys
from pathlib import Path

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.orchestrator import Pipeline
from src.validators.business_rules import BusinessRulesValidator


def main():
    """Run complete demonstration."""
    parser = argparse.ArgumentParser(
        description="Complete ETL demonstration with validation"
    )
    parser.add_argument(
        "source_dir",
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "--output",
        default="demo_results.json",
        help="Output JSON file"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("BID PDF PROCESSOR - COMPLETE DEMONSTRATION")
    print("="*70 + "\n")
    
    # Step 1: Run extraction pipeline
    print("📄 Step 1: Running Extraction Pipeline...")
    print("-" * 70)
    pipeline = Pipeline(args.source_dir)
    results = pipeline.process_directory()
    summary = pipeline.get_summary()
    
    print(f"\n✅ Extraction Complete!")
    print(f"   • Processed: {summary['total_files']} files")
    print(f"   • Success Rate: {summary['success_rate']}")
    print(f"   • Successful: {summary['successful']}")
    print(f"   • Failed: {summary['failed']}")
    print(f"   • Skipped: {summary['skipped']}\n")
    
    # Step 2: Validation
    print("\n🔍 Step 2: Running Data Validation...")
    print("-" * 70)
    validator = BusinessRulesValidator()
    
    validation_results = []
    valid_count = 0
    invalid_count = 0
    
    for result in results:
        if result.get('status') == 'success':
            validation = validator.validate_all(result)
            validation_results.append(validation)
            if validation['valid']:
                valid_count += 1
            else:
                invalid_count += 1
    
    print(f"\n✅ Validation Complete!")
    print(f"   • Validated: {len(validation_results)} extractions")
    print(f"   • Valid: {valid_count}")
    print(f"   • Invalid: {invalid_count}")
    
    if invalid_count > 0:
        print(f"\n⚠️  Issues Found:")
        for validation in validation_results:
            if not validation['valid']:
                file_name = Path(validation['file_path']).name
                print(f"   • {file_name}")
                for rule, (valid, msg) in validation['validations'].items():
                    if not valid:
                        print(f"      - {rule}: {msg}")
    
    # Step 3: Generate metrics
    print("\n\n📊 Step 3: Generating Metrics...")
    print("-" * 70)
    
    # Calculate completeness scores
    completeness_scores = []
    for result in results:
        if result.get('status') == 'success' and 'data' in result:
            data = result['data']
            total_fields = len(data)
            filled_fields = sum(1 for v in data.values() if v is not None and v != "")
            score = (filled_fields / total_fields * 100) if total_fields > 0 else 0
            completeness_scores.append(score)
    
    avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
    
    # Processing performance
    processing_times = []
    for result in results:
        if 'metadata' in result and 'processing_time' in result['metadata']:
            processing_times.append(result['metadata']['processing_time'])
    
    avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
    total_time = sum(processing_times)
    
    print(f"\n📈 Data Quality Metrics:")
    print(f"   • Average Completeness: {avg_completeness:.1f}%")
    print(f"   • Validation Pass Rate: {(valid_count/len(validation_results)*100):.1f}%")
    
    print(f"\n⚡ Performance Metrics:")
    print(f"   • Average Processing Time: {avg_time:.3f}s per document")
    print(f"   • Total Processing Time: {total_time:.2f}s")
    print(f"   • Throughput: {len(results)/total_time:.1f} documents/second")
    
    # Step 4: Save results
    print(f"\n\n💾 Step 4: Saving Results...")
    print("-" * 70)
    
    output_data = {
        "summary": {
            "extraction": summary,
            "validation": {
                "total": len(validation_results),
                "valid": valid_count,
                "invalid": invalid_count,
                "pass_rate": f"{(valid_count/len(validation_results)*100):.1f}%" if validation_results else "N/A"
            },
            "metrics": {
                "avg_completeness": f"{avg_completeness:.1f}%",
                "avg_processing_time": f"{avg_time:.3f}s",
                "throughput": f"{len(results)/total_time:.1f} docs/s"
            }
        },
        "extraction_results": results,
        "validation_results": validation_results
    }
    
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"✅ Results saved to: {output_path}")
    
    # Summary
    print("\n" + "="*70)
    print("🎉 DEMONSTRATION COMPLETE!")
    print("="*70)
    print(f"\nKey Achievements:")
    print(f"  ✓ {summary['successful']}/{summary['total_files']} documents successfully processed")
    print(f"  ✓ {summary['success_rate']} extraction success rate")
    print(f"  ✓ {avg_completeness:.1f}% average data completeness")
    print(f"  ✓ {avg_time:.3f}s average processing time")
    print(f"  ✓ Validated {len(validation_results)} extractions")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
