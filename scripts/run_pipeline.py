"""Main script to run the PDF extraction pipeline."""
import argparse
import json
import sys
from pathlib import Path

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.orchestrator import Pipeline
from src.loaders.postgres_loader import PostgresLoader


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract data from bid PDF documents"
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
        "--output",
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print summary statistics"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Skip unchanged files using cached fingerprints"
    )
    parser.add_argument(
        "--state-file",
        help="Optional path for incremental state cache"
    )
    parser.add_argument(
        "--load-postgres",
        action="store_true",
        help="Load extraction results into PostgreSQL"
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string (overrides DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    # Initialize and run pipeline
    pipeline = Pipeline(
        args.source_dir,
        incremental=args.incremental,
        state_file=args.state_file
    )
    results = pipeline.process_directory(args.pattern)
    
    # Get summary
    summary = pipeline.get_summary()
    
    # Print summary
    print("\n" + "="*60)
    print("PIPELINE EXECUTION SUMMARY")
    print("="*60)
    print(f"Total files processed: {summary['total_files']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Success rate: {summary['success_rate']}")
    print("\nBy Document Type:")
    for doc_type, stats in summary['by_document_type'].items():
        print(f"  {doc_type}: {stats['successful']}/{stats['total']} successful")
    print("="*60 + "\n")
    
    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                "summary": summary,
                "results": results if not args.summary_only else []
            }, f, indent=2, default=str)
        
        print(f"Results saved to: {output_path}")

    # Optional: Load results into PostgreSQL
    if args.load_postgres:
        print("\nLoading results into PostgreSQL...")
        try:
            loader = PostgresLoader(database_url=args.database_url)
            loader.create_tables()
            load_summary = loader.load_batch(results)
            loader.close()
            print(
                f"PostgreSQL load completed: {load_summary['successful']}/"
                f"{load_summary['total']} records ({load_summary['success_rate']})"
            )
        except Exception as e:
            print(f"PostgreSQL load failed: {e}")
    
    # Print individual results if not summary-only
    if not args.summary_only:
        print("\nSample Results (first 3):")
        print("-"*60)
        for result in results[:3]:
            print(f"\nFile: {Path(result['file_path']).name}")
            print(f"Type: {result.get('document_type', 'unknown')}")
            print(f"Status: {result.get('status', 'unknown')}")
            if result.get('status') == 'success' and result.get('data'):
                data = result['data']
                print(f"Extracted fields: {len(data)} fields")
                # Show sample fields
                for key, value in list(data.items())[:5]:
                    if value:
                        print(f"  {key}: {value}")
            elif result.get('error'):
                print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
