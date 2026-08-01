from typing import List, Dict, Any, Optional
import re


class ItineraryCleaner:
    """Clean and format itinerary data for storage"""
    
    def __init__(self):
        self.time_indicators = ["Morning", "Afternoon", "Evening", "Night"]
        self.max_activities_per_day = 5
    
    def clean(self, days_list: List[Dict]) -> List[Dict]:
        """
        Clean and format itinerary data
        
        Args:
            days_list: Raw itinerary data
        
        Returns:
            Cleaned itinerary data
        """
        if not days_list:
            return []
        
        cleaned = []
        for i, day_data in enumerate(days_list):
            cleaned_day = self._clean_day(day_data, i + 1)
            cleaned.append(cleaned_day)
        
        return cleaned
    
    def _clean_day(self, day_data: Dict, default_day: int) -> Dict:
        """Clean a single day's data"""
        # Get day number
        day_num = day_data.get("day", default_day)
        if not isinstance(day_num, int) or day_num < 1:
            day_num = default_day
        
        # Get and clean activities
        activities = day_data.get("activities", [])
        cleaned_activities = self._clean_activities(activities, day_num)
        
        return {
            "day": day_num,
            "activities": cleaned_activities
        }
    
    def _clean_activities(self, activities: List[str], day_num: int) -> List[str]:
        """Clean and format activities"""
        if not activities:
            return self._generate_fallback_activities(day_num)
        
        cleaned = []
        for activity in activities:
            if not activity or not isinstance(activity, str):
                continue
            
            activity = activity.strip()
            
            # Skip placeholder activities
            if self._is_placeholder(activity):
                continue
            
            # Add time indicator if missing
            activity = self._add_time_indicator(activity)
            
            # Clean up formatting
            activity = self._clean_formatting(activity)
            
            if activity and len(activity) > 5:
                cleaned.append(activity)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_activities = []
        for act in cleaned:
            if act not in seen:
                seen.add(act)
                unique_activities.append(act)
        
        # Limit activities
        if len(unique_activities) > self.max_activities_per_day:
            unique_activities = unique_activities[:self.max_activities_per_day]
        
        # Ensure minimum activities
        if len(unique_activities) < 2:
            unique_activities = self._generate_fallback_activities(day_num)
        
        return unique_activities
    
    def _is_placeholder(self, activity: str) -> bool:
        """Check if activity is a placeholder"""
        placeholders = [
            "placeholder", "tbd", "todo", "???", "to be determined",
            "add activity", "insert activity"
        ]
        return any(p in activity.lower() for p in placeholders)
    
    def _add_time_indicator(self, activity: str) -> str:
        """Add time indicator to activity if missing"""
        # Check if already has time indicator
        if any(indicator in activity for indicator in self.time_indicators):
            return activity
        
        # Determine appropriate time based on content
        activity_lower = activity.lower()
        
        if "breakfast" in activity_lower or "morning" in activity_lower:
            return f"Morning: {activity}"
        elif "lunch" in activity_lower or "afternoon" in activity_lower:
            return f"Afternoon: {activity}"
        elif "dinner" in activity_lower or "evening" in activity_lower:
            return f"Evening: {activity}"
        elif "night" in activity_lower or "club" in activity_lower:
            return f"Night: {activity}"
        else:
            # Default to morning
            return f"Morning: {activity}"
    
    def _clean_formatting(self, activity: str) -> str:
        """Clean up activity formatting"""
        # Remove multiple spaces
        activity = re.sub(r'\s+', ' ', activity)
        
        # Remove trailing punctuation
        activity = activity.rstrip('.,!?;')
        
        # Capitalize first letter
        if activity:
            activity = activity[0].upper() + activity[1:]
        
        return activity.strip()
    
    def _generate_fallback_activities(self, day_num: int) -> List[str]:
        """Generate fallback activities for a day"""
        return [
            f"Morning: Explore local attractions",
            f"Afternoon: Visit points of interest",
            f"Evening: Enjoy local cuisine"
        ]
    
    def add_weather_context(self, days_list: List[Dict], weather_data: Dict) -> List[Dict]:
        """
        Add weather context to activities
        
        Args:
            days_list: Cleaned itinerary data
            weather_data: Weather data keyed by day number
        
        Returns:
            Itinerary with weather context
        """
        if not weather_data:
            return days_list
        
        for day_data in days_list:
            day_num = day_data.get("day", 0)
            if day_num in weather_data:
                weather = weather_data[day_num]
                day_data["weather"] = {
                    "condition": weather.get("condition", ""),
                    "temperature": weather.get("temperature", 0)
                }
                
                # Add weather note to morning activity
                activities = day_data.get("activities", [])
                for i, activity in enumerate(activities):
                    if "Morning" in activity:
                        weather_note = (
                            f" 🌤️ {weather.get('condition', '')} | "
                            f"Temp: {weather.get('temperature', '')}°C"
                        )
                        # Add weather note if not already present
                        if "°C" not in activity:
                            activities[i] = activity + weather_note
                        break
        
        return days_list