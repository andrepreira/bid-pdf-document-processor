"""Data validation using business rules."""
from decimal import Decimal
from typing import Dict, List, Tuple

import structlog

logger = structlog.get_logger()


class BusinessRulesValidator:
    """Validate data against business rules."""
    
    def __init__(self):
        """Initialize validator."""
        self.validation_results = []
    
    def validate_contract_totals(self, contract_data: Dict, bidders: List[Dict]) -> Tuple[bool, str]:
        """Validate that contract awarded amount matches winning bidder.
        
        Args:
            contract_data: Contract information
            bidders: List of bidder information
            
        Returns:
            (is_valid, message) tuple
        """
        awarded_amount = contract_data.get('awarded_amount')
        awarded_to = contract_data.get('awarded_to')
        
        if not awarded_amount or not awarded_to:
            return True, "No award data to validate"
        
        # Find winning bidder
        winner = None
        for bidder in bidders:
            if bidder.get('is_winner') or bidder.get('bid_rank') == 1:
                winner = bidder
                break
        
        if not winner:
            return False, "Winner marked in contract but no winner found in bidders"
        
        bidder_amount = winner.get('total_bid_amount')
        if bidder_amount and abs(float(awarded_amount) - float(bidder_amount)) > 0.01:
            return False, f"Award amount mismatch: {awarded_amount} != {bidder_amount}"
        
        return True, "Contract totals validated"
    
    def validate_bid_items_sum(self, bidders: List[Dict], bid_items: List[Dict]) -> Tuple[bool, str]:
        """Validate that sum of bid items equals bidder total.
        
        Args:
            bidders: List of bidders
            bid_items: List of bid items
            
        Returns:
            (is_valid, message) tuple
        """
        if not bidders or not bid_items:
            return True, "No data to validate"
        
        # Group items by bidder
        items_by_bidder = {}
        for item in bid_items:
            bidder_name = item.get('bidder_name', 'unknown')
            if bidder_name not in items_by_bidder:
                items_by_bidder[bidder_name] = []
            items_by_bidder[bidder_name].append(item)
        
        # Validate each bidder
        mismatches = []
        for bidder in bidders:
            bidder_name = bidder.get('bidder_name')
            bidder_total = bidder.get('total_bid_amount')
            
            if not bidder_name or not bidder_total:
                continue
            
            # Sum items for this bidder
            items = items_by_bidder.get(bidder_name, [])
            items_sum = sum(
                float(item.get('total_price', 0)) 
                for item in items 
                if item.get('total_price')
            )
            
            # Check if sums match (with small tolerance)
            if abs(float(bidder_total) - items_sum) > 1.0:  # $1 tolerance
                mismatches.append(
                    f"{bidder_name}: total=${bidder_total}, items_sum=${items_sum}"
                )
        
        if mismatches:
            return False, f"Bid items sum mismatch: {'; '.join(mismatches)}"
        
        return True, "Bid items validated"
    
    def validate_dates(self, contract_data: Dict) -> Tuple[bool, str]:
        """Validate date logic (available < completion, etc.).
        
        Args:
            contract_data: Contract information
            
        Returns:
            (is_valid, message) tuple
        """
        from datetime import datetime
        
        date_available = contract_data.get('date_available')
        completion_date = contract_data.get('completion_date')
        bid_opening_date = contract_data.get('bid_opening_date')
        award_date = contract_data.get('award_date')
        
        # Parse dates
        dates = {}
        for key, value in [
            ('available', date_available),
            ('completion', completion_date),
            ('bid_opening', bid_opening_date),
            ('award', award_date)
        ]:
            if value:
                try:
                    if isinstance(value, str):
                        dates[key] = datetime.fromisoformat(value)
                    elif isinstance(value, datetime):
                        dates[key] = value
                except Exception:
                    pass
        
        # Validate date order
        if 'available' in dates and 'completion' in dates:
            if dates['available'] >= dates['completion']:
                return False, "Date available must be before completion date"
        
        if 'bid_opening' in dates and 'award' in dates:
            if dates['bid_opening'] > dates['award']:
                return False, "Bid opening must be before award date"
        
        if 'bid_opening' in dates and 'available' in dates:
            if dates['bid_opening'] >= dates['available']:
                return False, "Bid opening should be before availability date"
        
        return True, "Dates validated"
    
    def validate_goals(self, contract_data: Dict) -> Tuple[bool, str]:
        """Validate MBE/WBE goals consistency.
        
        Args:
            contract_data: Contract information
            
        Returns:
            (is_valid, message) tuple
        """
        mbe_goal = contract_data.get('mbe_goal')
        wbe_goal = contract_data.get('wbe_goal')
        combined_goal = contract_data.get('combined_goal')
        
        if None in [mbe_goal, wbe_goal, combined_goal]:
            return True, "Goals not all specified"
        
        # Combined should equal or exceed sum (sometimes it's just one)
        expected_combined = float(mbe_goal) + float(wbe_goal)
        actual_combined = float(combined_goal)
        
        if abs(actual_combined - expected_combined) > 0.1 and actual_combined < expected_combined:
            return False, f"Combined goal ({actual_combined}) inconsistent with MBE ({mbe_goal}) + WBE ({wbe_goal})"
        
        return True, "Goals validated"
    
    def validate_all(self, extraction_result: Dict) -> Dict:
        """Run all validation rules.
        
        Args:
            extraction_result: Full extraction result
            
        Returns:
            Validation report dictionary
        """
        if extraction_result.get('status') != 'success':
            return {'valid': True, 'message': 'Skipped validation for failed extraction'}
        
        data = extraction_result.get('data', {})
        contract_data = {k: v for k, v in data.items() if not isinstance(v, list)}
        bidders = data.get('bidders', [])
        bid_items = data.get('bid_items', [])
        
        validations = {
            'contract_totals': self.validate_contract_totals(contract_data, bidders),
            'bid_items_sum': self.validate_bid_items_sum(bidders, bid_items),
            'dates': self.validate_dates(contract_data),
            'goals': self.validate_goals(contract_data),
        }
        
        # Check if all validations passed
        all_valid = all(result[0] for result in validations.values())
        
        # Collect messages
        messages = {
            rule: msg 
            for rule, (valid, msg) in validations.items()
        }
        
        report = {
            'valid': all_valid,
            'validations': validations,
            'messages': messages,
            'file_path': extraction_result.get('file_path'),
        }
        
        if not all_valid:
            logger.warning(
                "Validation failed",
                file=extraction_result.get('file_path'),
                failed_rules=[k for k, (v, _) in validations.items() if not v]
            )
        
        return report
