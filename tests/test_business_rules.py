"""Unit tests for business rule validation."""
from __future__ import annotations

import pytest

from tests.mocks import data as mock_data


def test_validate_contract_totals_with_no_award_data(validator):
    contract_data = mock_data.make_contract_data(awarded_amount=None, awarded_to=None)
    is_valid, message = validator.validate_contract_totals(contract_data, [])
    assert is_valid is True
    assert "No award data" in message


def test_validate_contract_totals_with_matching_winner(validator):
    contract_data = mock_data.make_contract_data(awarded_amount=100.0, awarded_to="Acme Builders")
    bidders = mock_data.make_bidders(winner_total=100.0, include_winner=True)
    is_valid, message = validator.validate_contract_totals(contract_data, bidders)
    assert is_valid is True
    assert "validated" in message


def test_validate_contract_totals_with_mismatch(validator):
    contract_data = mock_data.make_contract_data(awarded_amount=100.0, awarded_to="Acme Builders")
    bidders = mock_data.make_bidders(winner_total=150.0, include_winner=True)
    is_valid, message = validator.validate_contract_totals(contract_data, bidders)
    assert is_valid is False
    assert "mismatch" in message


def test_validate_bid_items_sum_matches(validator):
    bidders = mock_data.make_bidders(
        winner_total=100.0,
        include_winner=True,
        include_competitor=False,
    )
    bid_items = mock_data.make_bid_items(bidder_name="Acme Builders", totals=[40.0, 60.0])
    is_valid, message = validator.validate_bid_items_sum(bidders, bid_items)
    assert is_valid is True
    assert "validated" in message


def test_validate_bid_items_sum_mismatch(validator):
    bidders = mock_data.make_bidders(
        winner_total=100.0,
        include_winner=True,
        include_competitor=False,
    )
    bid_items = mock_data.make_bid_items(bidder_name="Acme Builders", totals=[10.0, 20.0])
    is_valid, message = validator.validate_bid_items_sum(bidders, bid_items)
    assert is_valid is False
    assert "mismatch" in message


def test_validate_bidder_outliers_detected(validator):
    bidders = mock_data.make_outlier_bidders()
    is_valid, message = validator.validate_bidder_outliers(bidders)
    assert is_valid is False
    assert "Outlier" in message


def test_validate_bidder_outliers_insufficient_data(validator):
    bidders = [
        {"bidder_name": "A", "total_bid_amount": 100.0},
        {"bidder_name": "B", "total_bid_amount": 105.0},
        {"bidder_name": "C", "total_bid_amount": 110.0},
    ]
    is_valid, message = validator.validate_bidder_outliers(bidders)
    assert is_valid is True
    assert "Insufficient" in message


def test_validate_dates_order_ok(validator):
    contract_data = mock_data.make_date_contract_data(available_offset=10, completion_offset=40)
    is_valid, message = validator.validate_dates(contract_data)
    assert is_valid is True
    assert "validated" in message


def test_validate_dates_order_invalid_available_completion(validator):
    contract_data = mock_data.make_date_contract_data(available_offset=50, completion_offset=40)
    is_valid, message = validator.validate_dates(contract_data)
    assert is_valid is False
    assert "before completion" in message


def test_validate_goals_consistent(validator):
    contract_data = mock_data.make_contract_data(mbe_goal=2.0, wbe_goal=3.0, combined_goal=5.0)
    is_valid, message = validator.validate_goals(contract_data)
    assert is_valid is True
    assert "validated" in message


def test_validate_goals_inconsistent(validator):
    contract_data = mock_data.make_contract_data(mbe_goal=2.0, wbe_goal=3.0, combined_goal=4.0)
    is_valid, message = validator.validate_goals(contract_data)
    assert is_valid is False
    assert "inconsistent" in message


def test_validate_all_success(validator):
    extraction_result = mock_data.make_extraction_result()
    report = validator.validate_all(extraction_result)
    assert report["valid"] is True
    assert report["file_path"] == extraction_result["file_path"]
    assert "validations" in report
    assert "messages" in report


def test_validate_all_skips_failed_extraction(validator):
    report = validator.validate_all({"status": "failed"})
    assert report["valid"] is True
    assert "Skipped" in report["message"]
