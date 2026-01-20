"""Centralized mock data builders for tests."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List


def make_contract_data(
    *,
    awarded_amount: float | None = 100.0,
    awarded_to: str | None = "Acme Builders",
    date_available: str | datetime | None = "2024-01-10",
    completion_date: str | datetime | None = "2024-02-10",
    bid_opening_date: str | datetime | None = "2024-01-01",
    award_date: str | datetime | None = "2024-01-05",
    mbe_goal: float | None = 2.0,
    wbe_goal: float | None = 3.0,
    combined_goal: float | None = 5.0,
) -> Dict:
    return {
        "awarded_amount": awarded_amount,
        "awarded_to": awarded_to,
        "date_available": date_available,
        "completion_date": completion_date,
        "bid_opening_date": bid_opening_date,
        "award_date": award_date,
        "mbe_goal": mbe_goal,
        "wbe_goal": wbe_goal,
        "combined_goal": combined_goal,
    }


def make_bidders(
    *,
    winner_total: float = 100.0,
    include_winner: bool = True,
    include_ranked_winner: bool = False,
    include_competitor: bool = False,
) -> List[Dict]:
    bidders: List[Dict] = []

    if include_competitor:
        bidders.append(
            {
                "bidder_name": "Budget Co",
                "total_bid_amount": 120.0,
                "bid_rank": 2,
                "is_winner": False,
            }
        )

    if include_winner:
        bidders.append(
            {
                "bidder_name": "Acme Builders",
                "total_bid_amount": winner_total,
                "bid_rank": 1 if include_ranked_winner else 2,
                "is_winner": not include_ranked_winner,
            }
        )

    return bidders


def make_bid_items(
    *,
    bidder_name: str = "Acme Builders",
    totals: List[float] | None = None,
) -> List[Dict]:
    if totals is None:
        totals = [40.0, 60.0]
    return [
        {
            "bidder_name": bidder_name,
            "total_price": value,
        }
        for value in totals
    ]


def make_outlier_bidders() -> List[Dict]:
    return [
        {"bidder_name": "A", "total_bid_amount": 100.0},
        {"bidder_name": "B", "total_bid_amount": 105.0},
        {"bidder_name": "C", "total_bid_amount": 110.0},
        {"bidder_name": "D", "total_bid_amount": 5000.0},
        {"bidder_name": "E", "total_bid_amount": 115.0},
    ]


def make_date_contract_data(*, available_offset: int = 10, completion_offset: int = 40) -> Dict:
    base_date = datetime(2024, 1, 1)
    return make_contract_data(
        date_available=(base_date + timedelta(days=available_offset)).isoformat(),
        completion_date=(base_date + timedelta(days=completion_offset)).isoformat(),
        bid_opening_date=(base_date + timedelta(days=2)).isoformat(),
        award_date=(base_date + timedelta(days=5)).isoformat(),
    )


def make_extraction_result(
    *,
    contract_data: Dict | None = None,
    bidders: List[Dict] | None = None,
    bid_items: List[Dict] | None = None,
) -> Dict:
    if contract_data is None:
        contract_data = make_contract_data()
    if bidders is None:
        bidders = make_bidders(include_competitor=False)
    if bid_items is None:
        bid_items = make_bid_items()

    data = dict(contract_data)
    data["bidders"] = bidders
    data["bid_items"] = bid_items

    return {
        "status": "success",
        "data": data,
        "file_path": "source/sample.pdf",
    }
