# AI Vacation Planner - Backend API

## Overview

An intelligent vacation planning assistant backend API built with FastAPI. This system helps users plan trips end-to-end by managing destinations, itineraries, and user authentication.

## Features

- **User Authentication**: JWT-based registration and login
- **Trip Management**: Create, read, update, and delete trips
- **Itinerary Planning**: Store day-by-day activities for each trip
- **UUID Support**: Secure, non-sequential IDs for all entities
- **Production-Ready Architecture**: Clean separation of concerns with Controller-Service-Repository pattern
- **API Documentation**: Automatic Swagger UI and ReDoc endpoints

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **ORM**: SQLAlchemy 2.0.35
- **Database**: PostgreSQL (or SQLite for development)
- **Authentication**: JWT with bcrypt hashing
- **Validation**: Pydantic 2.7.4
- **Server**: Uvicorn

## Architecture

The project follows a clean **separation of concerns** pattern:

```
Controllers (HTTP layer)
    ↓
Services (Business logic)
    ↓
Repositories (Data access)
    ↓
Models (Database schema)
```

- **Controllers**: Handle HTTP requests/responses, input validation, authentication
- **Services**: Contain business logic and orchestrate repositories
- **Repositories**: Encapsulate database operations
- **Models**: SQLAlchemy ORM models defining database structure
- **Schemas**: Pydantic models for request/response validation

## Prerequisites

- Python 3.9 or higher (3.11 recommended)
- PostgreSQL (optional - SQLite works for development)
- pip (Python package manager)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ai-vacation-planner
```

### 2. Create Virtual Environment

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# For PostgreSQL
DATABASE_URL=postgresql://username:password@localhost:5432/vacation_planner

# For SQLite (development only)
# DATABASE_URL=sqlite:///./vacation_planner.db

SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
DATABASE_POOL_SIZE=10
```

### 5. Database Setup

#### Using PostgreSQL (Recommended)

```bash
# Create database
createdb vacation_planner

# Run migrations (if using Alembic)
alembic upgrade head
```

#### Using SQLite (Simpler for Development)

Just set `DATABASE_URL=sqlite:///./vacation_planner.db` in your `.env` file. The database file will be created automatically.

### 6. Run the Application

```bash
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

## API Documentation

Once running, access the interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

| Method | Endpoint         | Description                |
| ------ | ---------------- | -------------------------- |
| POST   | `/auth/register` | Register new user          |
| POST   | `/auth/login`    | Login and get access token |

### Trips

| Method | Endpoint           | Description          |
| ------ | ------------------ | -------------------- |
| POST   | `/trips/`          | Create a new trip    |
| GET    | `/trips/`          | Get all user's trips |
| GET    | `/trips/{trip_id}` | Get specific trip    |
| PUT    | `/trips/{trip_id}` | Update trip          |
| DELETE | `/trips/{trip_id}` | Delete trip          |

### Itineraries

| Method | Endpoint                 | Description                        |
| ------ | ------------------------ | ---------------------------------- |
| POST   | `/itineraries/`          | Create/update itinerary for a trip |
| GET    | `/itineraries/{trip_id}` | Get itinerary for a trip           |

## Usage Examples

### 1. Register a User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "traveler",
    "password": "securepass123",
    "full_name": "Travel User"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

Save the `access_token` from the response for subsequent requests.

### 3. Create a Trip

```bash
curl -X POST "http://localhost:8000/trips/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Paris",
    "days": 5,
    "budget": 1500,
    "trip_style": "budget"
  }'
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "destination": "Paris",
  "days": 5,
  "budget": 1500,
  "trip_style": "budget",
  "message": "Trip created successfully"
}
```

### 4. Create an Itinerary

```bash
curl -X POST "http://localhost:8000/itineraries/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trip_id": "550e8400-e29b-41d4-a716-446655440000",
    "days": [
      {
        "day": 1,
        "activities": ["Eiffel Tower", "Seine River Walk"]
      },
      {
        "day": 2,
        "activities": ["Louvre Museum", "Montmartre"]
      }
    ]
  }'
```

**Response:**

```json
{
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "itinerary": [
    {
      "day": 1,
      "activities": ["Eiffel Tower", "Seine River Walk"]
    },
    {
      "day": 2,
      "activities": ["Louvre Museum", "Montmartre"]
    }
  ],
  "message": "Itinerary created successfully"
}
```

### 5. Get All Trips

```bash
curl -X GET "http://localhost:8000/trips/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Get Specific Itinerary

```bash
curl -X GET "http://localhost:8000/itineraries/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7. Update a Trip

```bash
curl -X PUT "http://localhost:8000/trips/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 2000,
    "days": 7
  }'
```

### 8. Delete a Trip

```bash
curl -X DELETE "http://localhost:8000/trips/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```
ai-vacation-planner/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/                   # Core configuration
│   │   ├── config.py          # Environment settings
│   │   ├── database.py        # Database connection
│   │   ├── security.py        # JWT and password hashing
│   │   └── dependencies.py    # FastAPI dependencies
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── trip.py
│   │   └── itinerary.py
│   ├── schemas/                # Pydantic schemas (DTOs)
│   │   ├── user.py
│   │   ├── trip.py
│   │   └── itinerary.py
│   ├── repositories/           # Data access layer
│   │   ├── base_repository.py
│   │   ├── user_repository.py
│   │   ├── trip_repository.py
│   │   └── itinerary_repository.py
│   ├── services/               # Business logic layer
│   │   ├── auth_service.py
│   │   ├── trip_service.py
│   │   └── itinerary_service.py
│   └── controllers/            # HTTP request handlers
│       ├── auth_controller.py
│       ├── trip_controller.py
│       └── itinerary_controller.py
├── tests/                      # Unit tests
│   ├── test_auth.py
│   ├── test_trips.py
│   └── test_itineraries.py
├── .env                        # Environment variables
├── .env.example                # Example environment variables
├── .gitignore
├── requirements.txt
├── pyproject.toml             # Type checking configuration
└── README.md
```

### Database Management

```bash
# Reset database (PostgreSQL)
psql -c "DROP DATABASE IF EXISTS vacation_planner;"
psql -c "CREATE DATABASE vacation_planner;"

# Reset database (SQLite)
rm vacation_planner.db
```

### View Database Contents

```bash
# PostgreSQL
psql -d vacation_planner -c "SELECT * FROM users;"
psql -d vacation_planner -c "SELECT * FROM trips;"
psql -d vacation_planner -c "SELECT * FROM itineraries;"

# SQLite
sqlite3 vacation_planner.db "SELECT * FROM users;"
sqlite3 vacation_planner.db "SELECT * FROM trips;"
sqlite3 vacation_planner.db "SELECT * FROM itineraries;"
```
