from typing import List, Dict, Any, Optional, Tuple
import re


class ItineraryValidator:
    """Validate itinerary data for quality and completeness"""
    
    def __init__(self):
        self.time_indicators = ["Morning", "Afternoon", "Evening", "Night"]
    
    def validate(self, days_list: List[Dict], expected_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate itinerary data
        
        Args:
            days_list: List of day dictionaries
            expected_days: Expected number of days
        
        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []
        
        if not days_list:
            errors.append("Itinerary is empty")
            return self._result(False, errors, warnings)
        
        # Check day count
        if expected_days and len(days_list) != expected_days:
            warnings.append(f"Expected {expected_days} days, got {len(days_list)}")
        
        # Validate each day
        day_numbers = []
        for i, day_data in enumerate(days_list):
            day_errors = self._validate_day(day_data, i + 1)
            errors.extend(day_errors)
            
            day_num = day_data.get("day")
            if day_num is not None:
                day_numbers.append(day_num)
        
        # Check day sequence
        if day_numbers:
            errors.extend(self._validate_sequence(day_numbers))
        
        return self._result(len(errors) == 0, errors, warnings)
    
    def _validate_day(self, day_data: Dict, index: int) -> List[str]:
        """Validate a single day's data"""
        errors = []
        
        # Check day number
        if "day" not in day_data:
            errors.append(f"Day {index}: Missing day number")
        elif not isinstance(day_data["day"], int):
            errors.append(f"Day {index}: Day number must be integer")
        
        # Check activities
        activities = day_data.get("activities", [])
        if not activities:
            errors.append(f"Day {index}: No activities found")
            return errors
        
        if len(activities) < 2:
            errors.append(f"Day {index}: At least 2 activities required")
        
        if len(activities) > 6:
            warnings = []
            warnings.append(f"Day {index}: Too many activities ({len(activities)})")
            # Return warnings separately in full validation
        
        # Validate each activity
        for j, activity in enumerate(activities):
            if not isinstance(activity, str):
                errors.append(f"Day {index}, Activity {j+1}: Must be string")
                continue
            
            if not activity.strip():
                errors.append(f"Day {index}, Activity {j+1}: Empty activity")
                continue
            
            # Check for time indicator
            has_time = any(indicator in activity for indicator in self.time_indicators)
            if not has_time:
                errors.append(
                    f"Day {index}, Activity {j+1}: Missing time indicator "
                    f"({', '.join(self.time_indicators)})"
                )
            
            # Check for placeholders
            placeholders = ["placeholder", "tbd", "todo", "???"]
            if any(p in activity.lower() for p in placeholders):
                errors.append(
                    f"Day {index}, Activity {j+1}: Contains placeholder: '{activity}'"
                )
        
        return errors
    
    def _validate_sequence(self, day_numbers: List[int]) -> List[str]:
        """Validate day sequence"""
        errors = []
        
        sorted_days = sorted(day_numbers)
        
        if sorted_days[0] != 1:
            errors.append("Itinerary should start from day 1")
        
        if len(set(day_numbers)) != len(day_numbers):
            errors.append("Duplicate day numbers found")
        
        # Check for missing days
        for i in range(1, len(sorted_days)):
            if sorted_days[i] != sorted_days[i-1] + 1:
                errors.append(f"Missing day {sorted_days[i-1] + 1}")
        
        return errors
    
    def _result(self, valid: bool, errors: List[str], warnings: List[str]) -> Dict[str, Any]:
        """Create validation result dictionary"""
        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings)
        }
    
    def can_fix(self, validation_result: Dict) -> bool:
        """Check if validation issues can be fixed automatically"""
        # Can fix sequencing issues, missing activities, etc.
        errors = validation_result.get("errors", [])
        for error in errors:
            if "placeholder" in error.lower():
                return False  # Can't fix placeholder content
        return True
    
    def get_fix_suggestions(self, validation_result: Dict) -> List[str]:
        """Get suggestions for fixing validation issues"""
        suggestions = []
        
        for error in validation_result.get("errors", []):
            if "day number" in error.lower():
                suggestions.append("Reassign day numbers sequentially")
            elif "activities" in error.lower() and "empty" in error.lower():
                suggestions.append("Add activities to empty days")
            elif "time indicator" in error.lower():
                suggestions.append("Add time indicators (Morning/Afternoon/Evening)")
        
        return list(set(suggestions))