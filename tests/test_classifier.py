"""Unit tests for document classifier."""
from __future__ import annotations

import pytest

from pipeline.classifier import DocumentClassifier, DocumentType
from tests.mocks.pdf import FakePage, FakePdfReader


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("Invitation to Bid.pdf", DocumentType.INVITATION_TO_BID),
        ("Bid Tabs.pdf", DocumentType.BID_TABS),
        ("Award Letter.pdf", DocumentType.AWARD_LETTER),
        ("Item C Report.pdf", DocumentType.ITEM_C_REPORT),
        ("Bid Summary.pdf", DocumentType.BID_SUMMARY),
        ("Bids As Read.pdf", DocumentType.BIDS_AS_READ),
        ("Other.pdf", DocumentType.UNKNOWN),
    ],
)
def test_classify_by_filename(filename, expected):
    classifier = DocumentClassifier(filename)
    assert classifier.classify_filename_only() == expected


def test_classify_by_content_invitation(monkeypatch):
    classifier = DocumentClassifier("unknown.pdf")
    fake_reader = FakePdfReader([FakePage("Notice to Prospective Bidders")])
    monkeypatch.setattr("pipeline.classifier.pypdf.PdfReader", lambda _: fake_reader)
    assert classifier.classify() == DocumentType.INVITATION_TO_BID


def test_classify_by_content_award_letter(monkeypatch):
    classifier = DocumentClassifier("unknown.pdf")
    fake_reader = FakePdfReader([FakePage("Notification of Award")])
    monkeypatch.setattr("pipeline.classifier.pypdf.PdfReader", lambda _: fake_reader)
    assert classifier.classify() == DocumentType.AWARD_LETTER


def test_classify_by_content_item_c(monkeypatch):
    classifier = DocumentClassifier("unknown.pdf")
    fake_reader = FakePdfReader([FakePage("Item C $ Totals % Diff")])
    monkeypatch.setattr("pipeline.classifier.pypdf.PdfReader", lambda _: fake_reader)
    assert classifier.classify() == DocumentType.ITEM_C_REPORT


def test_classify_by_content_bid_tabs(monkeypatch):
    classifier = DocumentClassifier("unknown.pdf")
    fake_reader = FakePdfReader([FakePage("Roadway Items Bidder")])
    monkeypatch.setattr("pipeline.classifier.pypdf.PdfReader", lambda _: fake_reader)
    assert classifier.classify() == DocumentType.BID_TABS


def test_classify_by_content_bids_as_read(monkeypatch):
    classifier = DocumentClassifier("unknown.pdf")
    fake_reader = FakePdfReader([FakePage("Bids as read")])
    monkeypatch.setattr("pipeline.classifier.pypdf.PdfReader", lambda _: fake_reader)
    assert classifier.classify() == DocumentType.BIDS_AS_READ


def test_classify_by_content_unknown_on_empty(monkeypatch):
    classifier = DocumentClassifier("unknown.pdf")
    fake_reader = FakePdfReader([])
    monkeypatch.setattr("pipeline.classifier.pypdf.PdfReader", lambda _: fake_reader)
    assert classifier.classify() == DocumentType.UNKNOWN


def test_get_extractor_class_mapping():
    invite_cls = DocumentClassifier.get_extractor_class(DocumentType.INVITATION_TO_BID)
    bid_tabs_cls = DocumentClassifier.get_extractor_class(DocumentType.BID_TABS)
    bid_summary_cls = DocumentClassifier.get_extractor_class(DocumentType.BID_SUMMARY)
    bids_as_read_cls = DocumentClassifier.get_extractor_class(DocumentType.BIDS_AS_READ)
    award_cls = DocumentClassifier.get_extractor_class(DocumentType.AWARD_LETTER)
    item_c_cls = DocumentClassifier.get_extractor_class(DocumentType.ITEM_C_REPORT)

    assert invite_cls is not None and invite_cls.__name__ == "InvitationToBidExtractor"
    assert bid_tabs_cls is not None and bid_tabs_cls.__name__ == "BidTabsExtractor"
    assert bid_summary_cls is not None and bid_summary_cls.__name__ == "BidSummaryExtractor"
    assert bids_as_read_cls is not None and bids_as_read_cls.__name__ == "BidsAsReadExtractor"
    assert award_cls is not None and award_cls.__name__ == "AwardLetterExtractor"
    assert item_c_cls is not None and item_c_cls.__name__ == "ItemCExtractor"
    assert DocumentClassifier.get_extractor_class(DocumentType.UNKNOWN) is None
