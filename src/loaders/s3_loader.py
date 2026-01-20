"""S3 loader for processed outputs and file moves."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import boto3
except ImportError:  # pragma: no cover - optional for tests
    boto3 = None
import structlog

logger = structlog.get_logger()


class S3Loader:
    """Upload results and move files across S3 prefixes."""

    def __init__(
        self,
        bucket: str,
        processed_prefix: str,
        error_prefix: str,
        s3_client=None,
    ) -> None:
        self.bucket = bucket
        self.processed_prefix = processed_prefix
        self.error_prefix = error_prefix
        if s3_client is None and boto3 is None:
            raise ImportError("boto3 is required for S3 loading")
        self.s3 = s3_client or boto3.client("s3")

    def upload_results(self, results: List[dict], output_format: str) -> str:
        """Upload results to S3 as parquet or jsonl.

        Returns the S3 key of the uploaded object.
        """
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_format = output_format.lower()
        output_dir = Path("/tmp") / "pdf-results"
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_format == "parquet":
            output_path = output_dir / f"results_{run_id}.parquet"
            import pandas as pd
            df = pd.json_normalize(results)
            df.to_parquet(output_path, index=False)
        else:
            output_path = output_dir / f"results_{run_id}.jsonl"
            with open(output_path, "w", encoding="utf-8") as f:
                for row in results:
                    f.write(json.dumps(row))
                    f.write("\n")

        s3_key = f"{self.processed_prefix.rstrip('/')}/results/{output_path.name}"
        logger.info("Uploading results", key=s3_key)
        self.s3.upload_file(str(output_path), self.bucket, s3_key)
        return s3_key

    def move_source(self, key: str, success: bool) -> str:
        """Move raw file to processed or error prefix.

        Returns the new key.
        """
        filename = Path(key).name
        target_prefix = self.processed_prefix if success else self.error_prefix
        new_key = f"{target_prefix.rstrip('/')}/{filename}"
        logger.info("Moving S3 object", source=key, destination=new_key)
        self.s3.copy_object(
            Bucket=self.bucket,
            CopySource={"Bucket": self.bucket, "Key": key},
            Key=new_key,
        )
        self.s3.delete_object(Bucket=self.bucket, Key=key)
        return new_key
