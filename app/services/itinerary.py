from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.ai.llm.itinerary_generator import LLMService
from ..repositories.itinerary import ItineraryRepository
from ..repositories.trip import TripRepository
from ..schemas.itinerary import ItineraryCreate
from uuid import UUID


class ItineraryService:
    def __init__(self, db: Session, llm_service: Optional[LLMService] = None):
        self.itinerary_repo = ItineraryRepository(db)
        self.trip_repo = TripRepository(db)
        self._llm_service = llm_service

    @property
    def llm_service(self) -> LLMService:
        if self._llm_service is None:
            self._llm_service = LLMService()
        return self._llm_service

    def create_itinerary(self, user_id: UUID, itinerary_data: ItineraryCreate, use_ai: bool = False) -> Optional[dict]:

        trip = self.trip_repo.get_user_trip(itinerary_data.trip_id, user_id)
        if not trip:
            return None
        days_list = None

        if use_ai:

            days_list = self.llm_service.generate_itinerary(
                destination=str(trip.destination),
                days=int(trip.days),  # type: ignore
                budget=float(trip.budget),  # type: ignore
                travel_style=str(trip.trip_style)
            )
        else:
            if itinerary_data.days:
                days_list = [day.model_dump() for day in itinerary_data.days]
            else:

                days_list = self.llm_service.generate_itinerary(
                    destination=str(trip.destination),
                    days=int(trip.days),  # type: ignore
                    budget=float(trip.budget),  # type: ignore
                    travel_style=str(trip.trip_style)
                )

        itinerary = self.itinerary_repo.upsert_itinerary(
            trip_id=itinerary_data.trip_id,
            days=days_list
        )

        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "message": f"Itinerary {'AI-generated ' if use_ai else 'created'} successfully"
        }

    def get_trip_itinerary(self, user_id: UUID, trip_id: UUID) -> Optional[Dict[str, Any]]:
        itinerary = self.itinerary_repo.get_trip_itinerary(trip_id, user_id)
        if not itinerary:
            return None

        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "created_at": itinerary.created_at,
            "updated_at": itinerary.updated_at
        }
