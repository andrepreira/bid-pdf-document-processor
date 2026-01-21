"""Tests for OCR alerting and new extractors."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractors.base_extractor import BaseExtractor
from extractors.bid_summary_extractor import BidSummaryExtractor
from extractors.bids_as_read_extractor import BidsAsReadExtractor
from pipeline.classifier import DocumentType
from pipeline.orchestrator import Pipeline
from tests.mocks.pdf import FakePage, FakePdfReader


class DummyExtractor(BaseExtractor):
    """Minimal extractor for testing BaseExtractor stats."""

    def extract(self):
        return {"contract_number": "DA00000"}


def test_base_extractor_text_stats(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    fake_reader = FakePdfReader([FakePage(""), FakePage("Some text")])
    monkeypatch.setattr("extractors.base_extractor.pypdf.PdfReader", lambda _: fake_reader)

    extractor = DummyExtractor(pdf_path)
    stats = extractor._extract_text_stats()

    assert stats["text_page_count"] == 2
    assert stats["text_pages_with_content"] == 1
    assert stats["text_length"] == len("Some text")


def test_pipeline_assess_needs_ocr_when_empty(tmp_path):
    pipeline = Pipeline(tmp_path)
    result = {
        "status": "success",
        "data": {},
        "metadata": {
            "text_length": 0,
            "text_pages_with_content": 0,
        },
    }

    needs_ocr, reasons = pipeline._assess_needs_ocr(result)

    assert needs_ocr is True
    assert "no_text_extracted" in reasons
    assert "empty_data" in reasons


def test_pipeline_assess_needs_ocr_when_ok(tmp_path):
    pipeline = Pipeline(tmp_path)
    result = {
        "status": "success",
        "data": {"contract_number": "DA12345", "bidders": [{"bidder_name": "ACME"}]},
        "metadata": {
            "text_length": 200,
            "text_pages_with_content": 1,
        },
    }

    needs_ocr, reasons = pipeline._assess_needs_ocr(result)

    assert needs_ocr is False
    assert reasons == []


def test_bids_as_read_extractor_parses_bidders(tmp_path, monkeypatch):
    pdf_path = tmp_path / "DA00543_Bids As Read.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    sample_text = "RILEY PAVING INC SUPPLY, NC 1,387,101.46 1"
    monkeypatch.setattr(BidsAsReadExtractor, "_extract_text_any", lambda self: sample_text)

    extractor = BidsAsReadExtractor(pdf_path)
    data = extractor.extract()

    assert data["contract_number"] == "DA00543"
    assert len(data["bidders"]) == 1
    assert data["bidders"][0]["bidder_name"] == "RILEY PAVING INC"
    assert data["bidders"][0]["total_bid_amount"] == 1387101.46
    assert data["bidders"][0]["bid_rank"] == 1


def test_bid_summary_extractor_parses_bidders(tmp_path, monkeypatch):
    pdf_path = tmp_path / "DA00573 Bid Summary.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    sample_text = "1 RILEY PAVING INC SUPPLY, NC 1,387,101.46 -15.9"
    monkeypatch.setattr(BidSummaryExtractor, "_extract_text_any", lambda self: sample_text)

    extractor = BidSummaryExtractor(pdf_path)
    data = extractor.extract()

    assert data["contract_number"] == "DA00573"
    assert len(data["bidders"]) == 1
    assert data["bidders"][0]["bidder_name"] == "RILEY PAVING INC"
    assert data["bidders"][0]["percentage_diff"] == -15.9
    assert data["bidders"][0]["bid_rank"] == 1


def test_pipeline_ocr_reextract_adds_metadata(tmp_path, monkeypatch):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    pipeline = Pipeline(tmp_path)
    ocr_path = tmp_path / "scan_ocr.pdf"
    ocr_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        pipeline.ocr_processor,
        "run",
        lambda _: (ocr_path, {"ocr_applied": True, "ocr_method": "ocrmypdf"}),
    )

    monkeypatch.setattr(
        pipeline,
        "_run_extraction",
        lambda **kwargs: {
            "status": "success",
            "data": {"contract_number": "DA12345"},
            "metadata": {},
        },
    )

    result = pipeline._attempt_ocr_and_reextract(
        extractor_class=DummyExtractor,
        original_pdf_path=pdf_path,
        doc_type=DocumentType.INVITATION_TO_BID,
        file_name_for_mapping=pdf_path.name,
        initial_result={"status": "partial", "data": {"contract_number": "DA12345"}, "metadata": {}},
    )

    assert result["metadata"]["ocr_applied"] is True
    assert result["metadata"]["ocr_method"] == "ocrmypdf"
    assert result["metadata"]["ocr_source_file"] == str(ocr_path)
    assert not ocr_path.exists()


def test_pipeline_skip_result_includes_run_id(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    pipeline = Pipeline(tmp_path, incremental=True)
    fingerprint = pipeline._compute_file_fingerprint(pdf_path)

    state = {str(pdf_path): fingerprint}
    pipeline.state_file.write_text(json.dumps(state), encoding="utf-8")

    results = pipeline.process_directory("**/*.pdf")

    assert len(results) == 1
    assert results[0]["status"] == "skipped"
    assert results[0]["metadata"]["run_id"] == pipeline.run_id
