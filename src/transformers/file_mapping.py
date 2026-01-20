"""Field mapping resolver and application logic."""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DEFAULT_FIELD_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "invitation_to_bid": {
        "mapping_name": "invitation_to_bid_default",
        "fields": [
            "contract_number",
            "wbs_element",
            "counties",
            "description",
            "date_available",
            "completion_date",
            "mbe_goal",
            "wbe_goal",
            "combined_goal",
            "bid_opening_date",
        ],
        "aliases": {},
    },
    "award_letter": {
        "mapping_name": "award_letter_default",
        "fields": [
            "contract_number",
            "awarded_to",
            "awarded_amount",
            "award_date",
            "wbs_element",
            "counties",
            "description",
        ],
        "aliases": {},
    },
    "bid_tabs": {
        "mapping_name": "bid_tabs_default",
        "fields": [
            "contract_number",
            "bidders",
            "bid_items",
        ],
        "aliases": {},
        "list_fields": {
            "bidders": {
                "fields": [
                    "bidder_name",
                    "bidder_location",
                    "total_bid_amount",
                    "bid_rank",
                    "percentage_diff",
                    "is_winner",
                ],
                "aliases": {},
            },
            "bid_items": {
                "fields": [
                    "item_number",
                    "item_code",
                    "description",
                    "quantity",
                    "unit",
                    "unit_price",
                    "total_price",
                    "bidder_name",
                ],
                "aliases": {},
            },
        },
    },
    "item_c_report": {
        "mapping_name": "item_c_report_default",
        "fields": [
            "contract_number",
            "proposal_length",
            "type_of_work",
            "location",
            "estimated_cost",
            "date_available",
            "completion_date",
            "bidders",
        ],
        "aliases": {},
        "list_fields": {
            "bidders": {
                "fields": [
                    "bidder_name",
                    "bidder_location",
                    "total_bid_amount",
                    "percentage_diff",
                    "bid_rank",
                    "is_winner",
                ],
                "aliases": {},
            }
        },
    },
}


class MappingResolver:
    """Resolve and load field mappings for a given document type."""

    def __init__(self, source_dir: Path, mapping_path: Optional[str] = None):
        self.source_dir = Path(source_dir)
        self.mapping_path = Path(mapping_path) if mapping_path else self._default_mapping_path()
        self.mappings = self._load_mappings()

    def _default_mapping_path(self) -> Path:
        env_path = os.getenv("FILE_MAPPING_PATH")
        if env_path:
            return Path(env_path)

        base_dir = self.source_dir.parent if self.source_dir.name else self.source_dir
        return base_dir / "file_mappings" / "field_mappings.json"

    def _load_mappings(self) -> Dict[str, Dict[str, Any]]:
        if self.mapping_path and self.mapping_path.exists():
            try:
                with open(self.mapping_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return DEFAULT_FIELD_MAPPINGS

    def resolve(self, document_type: str, file_name: str) -> Dict[str, Any]:
        mapping = self.mappings.get(document_type, {})
        mapping_source = "external" if self.mapping_path and self.mapping_path.exists() else "default"
        resolved = dict(mapping)
        resolved["mapping_source"] = mapping_source
        resolved["mapping_file"] = str(self.mapping_path) if self.mapping_path else None
        resolved["document_type"] = document_type
        resolved["file_name"] = file_name
        return resolved


def apply_mapping(data: Dict[str, Any], mapping: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Apply mapping to normalize and filter extracted data.

    Returns mapped data and mapping metadata.
    """
    if not mapping or not isinstance(data, dict):
        return data, {"applied": False}

    fields = mapping.get("fields", [])
    aliases = mapping.get("aliases", {})
    list_fields = mapping.get("list_fields", {})

    mapped: Dict[str, Any] = {}

    for field in fields:
        if field in data:
            mapped[field] = data[field]

    for alias, target in aliases.items():
        if target in fields and alias in data and target not in mapped:
            mapped[target] = data[alias]

    for list_name, list_mapping in list_fields.items():
        items = data.get(list_name, [])
        if not isinstance(items, list):
            continue
        mapped_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            mapped_items.append(_apply_item_mapping(item, list_mapping))
        mapped[list_name] = mapped_items

    metadata = {
        "applied": True,
        "mapping_name": mapping.get("mapping_name"),
        "mapping_source": mapping.get("mapping_source"),
        "mapping_file": mapping.get("mapping_file"),
        "document_type": mapping.get("document_type"),
        "expected_fields": fields,
    }

    return mapped, metadata


def _apply_item_mapping(item: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    fields = mapping.get("fields", [])
    aliases = mapping.get("aliases", {})

    mapped_item: Dict[str, Any] = {}
    for field in fields:
        if field in item:
            mapped_item[field] = item[field]

    for alias, target in aliases.items():
        if target in fields and alias in item and target not in mapped_item:
            mapped_item[target] = item[alias]

    return mapped_item
