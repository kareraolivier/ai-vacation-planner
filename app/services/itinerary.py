from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.itinerary import ItineraryRepository
from app.schemas.itinerary import ItineraryCreate
from app.services.weather import WeatherService
from app.services.trip import TripService
from app.llm.itinerary_generator import LLMService


class ItineraryService:
    """Service for managing itineraries"""
    
    def __init__(self, db: Session):
        self.itinerary_repo = ItineraryRepository(db)
        self.trip_service = TripService()
        self.llm_service = LLMService()
        self.weather_service = WeatherService()
    
    def create_itinerary(
        self, 
        user_id: UUID, 
        itinerary_data: ItineraryCreate
    ) -> Optional[Dict[str, Any]]:
      
        # Get trip and verify ownership
        trip = self.trip_service.get_user_trip(itinerary_data.trip_id, user_id)
        if not trip:
            return None
        
        # Validate provided days
        if not itinerary_data.days:
            return {
                "error": "No days provided",
                "message": "Please provide itinerary days"
            }
        
        # Convert to dict if needed
        days_list = []
        for day in itinerary_data.days:
            if hasattr(day, 'model_dump'):
                days_list.append(day.model_dump())
            else:
                days_list.append(day)
        
        # Save to database
        itinerary = self.itinerary_repo.upsert_itinerary(
            trip_id=itinerary_data.trip_id,
            days=days_list
        )
        
        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "message": "Itinerary created successfully"
        }
    
    def ai_generate_itinerary(
        self,
        user_id: UUID,
        trip_id: UUID
    ) -> Optional[Dict[str, Any]]:
      
        # Get trip and verify ownership
        trip = self.trip_service.get_user_trip(trip_id, user_id)
        if not trip:
            return None
        
        # Generate itinerary using AI
        try:
            days_list = self.llm_service.generate_itinerary(
                destination=str(trip.destination),
                days=int(trip.days),
                budget=float(trip.budget) if trip.budget else 0,
                travel_style=str(trip.trip_style) if trip.trip_style else "balanced"
            )
        except Exception as error:
            return {
                "error": "AI generation failed",
                "message": str(error)
            }
        
        # Save to database
        itinerary = self.itinerary_repo.upsert_itinerary(
            trip_id=trip_id,
            days=days_list
        )
        
        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "message": "AI-generated itinerary created successfully"
        }
    
    def get_trip_itinerary(self, user_id: UUID, trip_id: UUID) -> Optional[Dict[str, Any]]:
        """Get itinerary for a trip"""
        itinerary = self.itinerary_repo.get_trip_itinerary(trip_id, user_id)
        if not itinerary:
            return None
        
        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "created_at": itinerary.created_at,
            "updated_at": itinerary.updated_at
        }
    
    def delete_itinerary(self, user_id: UUID, trip_id: UUID) -> bool:
        """Delete itinerary for a trip"""
        # Verify ownership
        trip = self.trip_service.get_user_trip(trip_id, user_id)
        if not trip:
            return False
        
        return self.itinerary_repo.delete_by_trip(trip_id)