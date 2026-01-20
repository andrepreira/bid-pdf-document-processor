"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.mocks import data as mock_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture()
def validator():
    from validators.business_rules import BusinessRulesValidator

    return BusinessRulesValidator()


@pytest.fixture()
def contract_data():
    return mock_data.make_contract_data()


@pytest.fixture()
def bidders():
    return mock_data.make_bidders()


@pytest.fixture()
def bid_items():
    return mock_data.make_bid_items()
