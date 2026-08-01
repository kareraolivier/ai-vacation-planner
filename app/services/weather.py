import httpx
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching weather data (OpenWeatherMap API)"""
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def get_weather_forecast(
        self, 
        city: str, 
        country: Optional[str] = None,
        days: int = 5
    ) -> Dict:
        """
        Fetch weather forecast for a city
        
        Args:
            city: City name
            country: Country code (optional)
            days: Number of days to forecast (max 5)
        
        Returns:
            Dict containing weather forecast data
        """
        if not self.api_key:
            logger.warning("OpenWeather API key not configured")
            return self._get_mock_weather(city, days)
        
        try:
            location_query = f"{city},{country}" if country else city
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get coordinates first
                geo_response = await client.get(
                    "http://api.openweathermap.org/geo/1.0/direct",
                    params={
                        "q": location_query,
                        "limit": 1,
                        "appid": self.api_key
                    }
                )
                geo_response.raise_for_status()
                geo_data = geo_response.json()
                
                if not geo_data:
                    raise ValueError(f"Location '{city}' not found")
                
                lat = geo_data[0]["lat"]
                lon = geo_data[0]["lon"]
                
                # Get 5-day forecast
                forecast_response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "units": "metric",
                        "cnt": days * 8,  # 8 readings per day (3-hour intervals)
                        "appid": self.api_key
                    }
                )
                forecast_response.raise_for_status()
                data = forecast_response.json()
                
                return self._format_forecast(data, days)
                
        except Exception as e:
            logger.error(f"Weather API error: {str(e)}")
            return self._get_mock_weather(city, days)
    
    def _format_forecast(self, data: Dict, days: int) -> Dict:
        """Format OpenWeatherMap forecast data"""
        forecasts = {}
        
        for item in data["list"][:days * 8]:
            date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
            if date not in forecasts:
                forecasts[date] = {
                    "date": date,
                    "temperatures": [],
                    "conditions": [],
                    "humidity": [],
                    "wind_speed": []
                }
            
            forecasts[date]["temperatures"].append(item["main"]["temp"])
            forecasts[date]["conditions"].append(item["weather"][0]["description"])
            forecasts[date]["humidity"].append(item["main"]["humidity"])
            forecasts[date]["wind_speed"].append(item["wind"]["speed"])
        
        # Process daily averages
        result = []
        for date, data in forecasts.items():
            result.append({
                "date": date,
                "avg_temp": round(sum(data["temperatures"]) / len(data["temperatures"]), 1),
                "min_temp": round(min(data["temperatures"]), 1),
                "max_temp": round(max(data["temperatures"]), 1),
                "condition": max(set(data["conditions"]), key=data["conditions"].count),
                "avg_humidity": round(sum(data["humidity"]) / len(data["humidity"])),
                "avg_wind_speed": round(sum(data["wind_speed"]) / len(data["wind_speed"]), 1)
            })
        
        return {
            "city": data["city"]["name"],
            "country": data["city"]["country"],
            "forecast": result[:days]
        }
    
    def _get_mock_weather(self, city: str, days: int) -> Dict:
        """Return mock weather data for testing"""
        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Clear"]
        result = []
        
        start_date = datetime.now()
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            result.append({
                "date": date,
                "avg_temp": round(20 + (i % 10), 1),
                "min_temp": round(15 + (i % 8), 1),
                "max_temp": round(25 + (i % 12), 1),
                "condition": conditions[i % len(conditions)],
                "avg_humidity": 60 + (i % 30),
                "avg_wind_speed": round(5 + (i % 15), 1)
            })
        
        return {
            "city": city,
            "country": "RW",
            "forecast": result,
            "_mock": True
        }
    
    async def get_weather_for_trip_days(
        self, 
        destination: str, 
        start_date: datetime,
        days: int
    ) -> Dict:
        """
        Get weather forecast for specific trip dates
        
        Args:
            destination: City name
            start_date: Trip start date
            days: Number of days
        
        Returns:
            Dict with weather data keyed by day number
        """
        forecast = await self.get_weather_forecast(destination, days=days)
        
        # Map forecast to day numbers
        weather_by_day = {}
        for i, day_data in enumerate(forecast.get("forecast", []), start=1):
            weather_by_day[i] = {
                "date": day_data["date"],
                "condition": day_data["condition"],
                "temperature": day_data["avg_temp"],
                "min_temp": day_data["min_temp"],
                "max_temp": day_data["max_temp"],
                "humidity": day_data["avg_humidity"],
                "wind_speed": day_data["avg_wind_speed"]
            }
        
        return weather_by_day