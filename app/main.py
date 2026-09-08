from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, Base
from .controllers import auth, trip, itinerary, knowledge

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Vacation Planner API",
    description=(
        "Backend API for trip planning. Users can manage trips and itineraries, "
        "ingest travel knowledge for RAG, and generate itineraries with Claude "
        "using retrieved destination context."
    ),
    version="1.1.0",
    openapi_tags=[
        {"name": "Authentication", "description": "Register and login"},
        {"name": "Trips", "description": "Create and manage trips"},
        {"name": "Itineraries", "description": "Manually create and retrieve itineraries"},
        {"name": "Knowledge Base", "description": "Ingest, re-index, and search travel knowledge"},
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(trip.router)
app.include_router(itinerary.router)
app.include_router(knowledge.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to AI Vacation Planner API"
    }

@app.get("/health")
def health_check():
    return {"status": "The app is healthy and running!"}