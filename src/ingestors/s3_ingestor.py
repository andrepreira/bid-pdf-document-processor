"""S3 ingestor for raw PDFs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import boto3
except ImportError:  # pragma: no cover - optional for tests
    boto3 = None
import structlog

logger = structlog.get_logger()


@dataclass
class IngestedFile:
    key: str
    local_path: Path


class S3Ingestor:
    """Download PDFs from S3 for processing."""

    def __init__(
        self,
        bucket: str,
        raw_prefix: str,
        local_dir: Path,
        max_items: Optional[int] = None,
        s3_client=None,
    ) -> None:
        self.bucket = bucket
        self.raw_prefix = raw_prefix
        self.local_dir = Path(local_dir)
        self.max_items = max_items
        if s3_client is None and boto3 is None:
            raise ImportError("boto3 is required for S3 ingestion")
        self.s3 = s3_client or boto3.client("s3")

    def list_pdf_keys(self) -> List[str]:
        """List PDF keys under the raw prefix."""
        paginator = self.s3.get_paginator("list_objects_v2")
        keys: List[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.raw_prefix):
            for item in page.get("Contents", []):
                key = item.get("Key", "")
                if key.lower().endswith(".pdf"):
                    keys.append(key)
                if self.max_items and len(keys) >= self.max_items:
                    return keys
        return keys

    def download_all(self) -> List[IngestedFile]:
        """Download all PDFs to the local directory."""
        self.local_dir.mkdir(parents=True, exist_ok=True)
        keys = self.list_pdf_keys()
        ingested: List[IngestedFile] = []
        for key in keys:
            filename = Path(key).name
            local_path = self.local_dir / filename
            logger.info("Downloading S3 object", key=key, dest=str(local_path))
            self.s3.download_file(self.bucket, key, str(local_path))
            ingested.append(IngestedFile(key=key, local_path=local_path))
        return ingested

    @staticmethod
    def build_key_map(files: Iterable[IngestedFile]) -> Dict[str, str]:
        """Map local file paths to S3 keys."""
        return {str(item.local_path): item.key for item in files}
