from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, Base
from .controllers import auth, trip, itinerary

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Vacation Planner API",
    description="Backend API for intelligent trip planning assistant",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(trip.router)
app.include_router(itinerary.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to AI Vacation Planner API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}