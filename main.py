"""Cloud entrypoint for S3-based ingestion and processing."""
from __future__ import annotations

import os
from pathlib import Path

import structlog

from src.ingestors.s3_ingestor import S3Ingestor
from src.loaders.s3_loader import S3Loader
from src.pipeline.orchestrator import Pipeline

logger = structlog.get_logger()


def main() -> None:
    bucket = os.getenv("S3_BUCKET")
    raw_prefix = os.getenv("S3_RAW_PREFIX", "raw/")
    processed_prefix = os.getenv("S3_PROCESSED_PREFIX", "processed/")
    error_prefix = os.getenv("S3_ERROR_PREFIX", "error/")
    output_format = os.getenv("OUTPUT_FORMAT", "parquet")
    batch_size = os.getenv("BATCH_SIZE")

    if not bucket:
        raise ValueError("S3_BUCKET is required")

    max_items = int(batch_size) if batch_size else None
    local_dir = Path("/tmp/pdf_ingest")

    ingestor = S3Ingestor(
        bucket=bucket,
        raw_prefix=raw_prefix,
        local_dir=local_dir,
        max_items=max_items,
    )
    ingested = ingestor.download_all()
    if not ingested:
        logger.info("No PDFs found for processing")
        return

    key_map = ingestor.build_key_map(ingested)

    pipeline = Pipeline(local_dir)
    results = pipeline.process_directory("**/*.pdf")

    loader = S3Loader(
        bucket=bucket,
        processed_prefix=processed_prefix,
        error_prefix=error_prefix,
    )
    loader.upload_results(results, output_format)

    for result in results:
        file_path = result.get("file_path")
        s3_key = key_map.get(file_path)
        if not s3_key:
            continue
        status = result.get("status")
        success = status in ("success", "partial")
        loader.move_source(s3_key, success=success)


if __name__ == "__main__":
    main()
