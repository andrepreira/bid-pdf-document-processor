"""OCR processing utilities."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import structlog

logger = structlog.get_logger()


class OCRProcessor:
    """Run OCR on PDFs using OCRmyPDF."""

    def __init__(self, enabled: Optional[bool] = None, timeout_seconds: int = 300):
        env_enabled = os.getenv("OCR_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"}
        env_timeout = os.getenv("OCR_TIMEOUT_SECONDS")
        if env_timeout and env_timeout.strip().isdigit():
            timeout_seconds = int(env_timeout)

        self.enabled = env_enabled if enabled is None else enabled
        self.timeout_seconds = timeout_seconds
        self.method = "ocrmypdf"

    def is_available(self) -> bool:
        return shutil.which(self.method) is not None

    def run(self, input_pdf: Path) -> Tuple[Optional[Path], Dict]:
        """Run OCR and return output PDF path and metadata."""
        if not self.enabled:
            return None, {"ocr_attempted": False, "ocr_enabled": False}

        if not self.is_available():
            return None, {
                "ocr_attempted": True,
                "ocr_enabled": True,
                "ocr_applied": False,
                "ocr_method": self.method,
                "ocr_error": "ocrmypdf_not_available",
            }

        start = time.time()
        output_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                output_path = Path(tmp.name)

            cmd = [
                self.method,
                "--skip-text",
                "--deskew",
                "--optimize",
                "1",
                str(input_pdf),
                str(output_path),
            ]

            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
            )

            duration = time.time() - start
            return output_path, {
                "ocr_attempted": True,
                "ocr_enabled": True,
                "ocr_applied": True,
                "ocr_method": self.method,
                "ocr_duration_seconds": duration,
            }
        except subprocess.TimeoutExpired as exc:
            logger.warning("OCR timed out", error=str(exc))
            return None, {
                "ocr_attempted": True,
                "ocr_enabled": True,
                "ocr_applied": False,
                "ocr_method": self.method,
                "ocr_error": "timeout",
            }
        except Exception as exc:
            logger.warning("OCR failed", error=str(exc))
            return None, {
                "ocr_attempted": True,
                "ocr_enabled": True,
                "ocr_applied": False,
                "ocr_method": self.method,
                "ocr_error": str(exc),
            }

