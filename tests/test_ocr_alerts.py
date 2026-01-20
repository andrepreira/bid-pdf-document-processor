"""Tests for OCR alerting and new extractors."""
from __future__ import annotations

from pathlib import Path

import pytest

from extractors.base_extractor import BaseExtractor
from extractors.bid_summary_extractor import BidSummaryExtractor
from extractors.bids_as_read_extractor import BidsAsReadExtractor
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
