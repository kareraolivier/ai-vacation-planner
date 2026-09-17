# AI Vacation Planner - Backend API

## Overview

An intelligent vacation planning assistant backend API built with FastAPI. Users can register, manage trips and itineraries, ingest travel knowledge, and generate itineraries with Claude using retrieved destination context.

## Features

- **User Authentication**: JWT-based registration and login
- **Trip Management**: Create, read, update, and delete trips
- **Itinerary Planning**: Store day-by-day activities for each trip
- **Travel Knowledge Base**: Ingest, chunk, embed, and semantically search travel documents
- **RAG-backed itineraries**: Claude generates day-by-day plans using retrieved knowledge when available
- **UUID Support**: Secure, non-sequential IDs for all entities
- **Production-Ready Architecture**: Controller-Service-Repository, with provider abstractions for LLM, embeddings, and vector storage
- **API Documentation**: Automatic Swagger UI and ReDoc endpoints

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2
- **Database**: PostgreSQL (or SQLite for development)
- **Vector store**: Qdrant (in-memory store available for tests)
- **LLM**: Claude via `app/ai/llm` (Anthropic)
- **Embeddings**: OpenAI-compatible models for RAG only
- **Authentication**: JWT with bcrypt hashing
- **Validation**: Pydantic 2
- **Server**: Uvicorn

## Architecture

The project still uses the original layered flow. AI capabilities live under `app/ai/`; `app/services/` stays use-case orchestration.

```
Controllers (HTTP layer)
    ↓
Services (Business logic, RAG, itinerary generation)
    ↓
Repositories (Data access)
    ↓
Models (Database schema)
```

```
POST /itineraries/{trip_id}/generate-ai
    ↓
ItineraryService
    ↓
KnowledgeService.retrieve_context (optional RAG)
    ↓
LLMService (Claude)
    ↓
Persist via existing itinerary repository
```

- **Controllers**: HTTP, validation, authentication
- **Services**: Business logic and RAG pipeline
- **Repositories**: Database operations
- **Models**: SQLAlchemy tables
- **Schemas**: Pydantic request/response models

### RAG architecture

```
Ingest request
    ↓
DocumentLoader
    ↓
TextChunker (LangChain recursive splitter)
    ↓
EmbeddingProvider (OpenAI or deterministic hash for tests)
    ↓
VectorStore (Qdrant or in-memory)
    ↓
KnowledgeDocument metadata in PostgreSQL/SQLite
```

At query time:

```
Search query
    ↓
embed query
    ↓
vector similarity search
    ↓
optional destination filter
    ↓
ranked chunks for API clients or generate-ai
```

- **Document metadata** (title, source, category, destination, full source text, content hash, chunk count) lives in the existing relational database.
- **Chunks and embeddings** live in the vector store.
- Re-ingesting the same `source` with unchanged content is a no-op. A changed document deletes that document's old vectors, then writes a fresh index. `POST /knowledge/documents/{id}/reindex` rebuilds vectors from stored source text.

### Chunking and embeddings

- Default chunk size is `RAG_CHUNK_SIZE` (800) with `RAG_CHUNK_OVERLAP` (120).
- Splitter prefers paragraph and sentence boundaries.
- Default embedding model is `text-embedding-3-small`.
- `EMBEDDING_PROVIDER=hash` is for tests and offline development only; it is not semantic.

### Vector database

Qdrant is the default production store because this project already uses a relational database for application data and had no vector engine. The `VectorStore` interface keeps Qdrant out of controllers and services.

```bash
docker compose up -d
```

For unit tests, `VECTOR_STORE_PROVIDER=memory` uses cosine search in process.

### LangChain

LangChain is used where it replaces code we would otherwise write ourselves:

- `RecursiveCharacterTextSplitter` for chunking
- `OpenAIEmbeddings` only when `EMBEDDING_PROVIDER=openai`

## How to learn this project

Study one request through the layers. If you can narrate *“Plan my Paris trip using the destination guide”* from HTTP to Claude and back, you understand the system.

### Read in this order

1. `app/main.py` — routers
2. `app/core/dependencies.py` — JWT
3. `app/controllers/trip.py` + `app/services/trip.py` — simplest CRUD
4. `app/controllers/itinerary.py` — `generate-ai` is the product AI entry
5. `app/services/itinerary.py` — loads the trip, retrieves knowledge, calls Claude
6. `app/services/knowledge.py` + `app/ai/rag/` — ingest and search
7. `app/ai/llm/` — Claude composer and JSON parser

`app/services/` is use cases. `app/ai/` is capabilities those use cases call.

### The path you should be able to draw

```
POST /itineraries/{trip_id}/generate-ai
    → ItineraryService (load trip)
    → KnowledgeService.retrieve_context (RAG; skipped if retrieval fails)
    → LLMService + PromptBuilder + ResponseParser
    → persist itinerary
    → { trip_id, itinerary, message }
```

### How to practice

1. Trace `KnowledgeService.ingest_document` (hash, chunk, embed, Qdrant).
2. Call `POST /knowledge/search`, then `POST /itineraries/{trip_id}/generate-ai`.
3. Open http://localhost:8000/docs and explain `generate-ai` vs `/knowledge/search`.

## Prerequisites

- Python 3.10 or higher (3.11 recommended)
- Docker Desktop (Postgres and Qdrant run in Compose; no local Postgres install needed)
- An Anthropic API key for itinerary generation
- An OpenAI-compatible embedding key only if you ingest/search the knowledge base with `EMBEDDING_PROVIDER=openai`
- pip

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

```bash
cp .env.example .env
```

See [Environment variables](#environment-variables) below.

### 5. Postgres and Qdrant (Docker)

Do not use a local Postgres install. Compose publishes Postgres on **host port 5433** so it does not collide with anything already bound to 5432. Qdrant stays on 6333.

```bash
docker compose up -d
docker compose ps
```

`.env.example` already points at this database:

```env
DATABASE_URL=postgresql://vacation:vacation@localhost:5433/vacation_planner
```

SQLite is still available if you do not want Docker for the database: `DATABASE_URL=sqlite:///./vacation_planner.db`. You still need Compose for Qdrant unless you set `VECTOR_STORE_PROVIDER=memory`.

Tables are created on API startup via SQLAlchemy `create_all`.

### 6. Run the Application

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database URL |
| `SECRET_KEY` | JWT signing key |
| `ALGORITHM` | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime |
| `ENVIRONMENT` | `development` enables SQL echo |
| `DATABASE_POOL_SIZE` | PostgreSQL pool size |
| `ANTHROPIC_API_KEY` | Claude API key used by `LLMService` |
| `LLM_MODEL` | Claude model (default `claude-haiku-4-5`) |
| `LLM_TEMPERATURE` | Sampling temperature |
| `LLM_MAX_TOKENS` | Max tokens for itinerary generation |
| `LLM_MAX_RETRIES` | Provider retries |
| `EMBEDDING_PROVIDER` | `openai` or `hash` |
| `EMBEDDING_MODEL` | Embedding model name |
| `EMBEDDING_API_KEY` | Embedding key |
| `EMBEDDING_DIMENSIONS` | Vector size |
| `VECTOR_STORE_PROVIDER` | `qdrant` or `memory` |
| `QDRANT_URL` | Qdrant HTTP URL |
| `QDRANT_API_KEY` | Optional Qdrant key |
| `QDRANT_COLLECTION` | Collection name |
| `QDRANT_TIMEOUT` | Client timeout |
| `RAG_CHUNK_SIZE` | Chunk size in characters |
| `RAG_CHUNK_OVERLAP` | Chunk overlap |
| `RAG_TOP_K` | Default retrieval depth |

Never commit real keys. `.env` is gitignored.

## Populate and re-index the knowledge base

Seed the bundled Paris, Tokyo, and Barcelona guides:

```bash
python scripts/seed_knowledge.py
```

Or ingest through the API:

```bash
curl -X POST "http://localhost:8000/knowledge/documents" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Paris Travel Guide",
    "source": "data/knowledge/paris.md",
    "category": "guide",
    "destination": "Paris",
    "content": "Paris rewards walkers..."
  }'
```

`source` is the upsert key. Sending the same source with new content replaces vectors for that document only.

Re-index from stored source text:

```bash
curl -X POST "http://localhost:8000/knowledge/documents/{document_id}/reindex" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## How to test RAG

1. Start the API with `EMBEDDING_PROVIDER=openai` and Qdrant running, or use `hash` + `memory` for a dry run.
2. Ingest a destination guide.
3. Call `POST /knowledge/search` with a natural-language query and optional `destination`.
4. Confirm returned chunks mention the ingested material.

```bash
curl -X POST "http://localhost:8000/knowledge/search" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What should I do in Paris when it rains?",
    "destination": "Paris",
    "top_k": 5
  }'
```

Automated coverage lives in `tests/test_chunker.py`, `tests/test_embeddings.py`, `tests/test_vector_store.py`, `tests/test_retriever.py`, and `tests/test_knowledge_api.py`.

```bash
pytest
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All new endpoints include request/response models, validation rules, and documented error responses.

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
| POST   | `/itineraries/{trip_id}/generate-ai` | Claude + retrieved knowledge, then save |

### Knowledge Base

| Method | Endpoint                                 | Description                          |
| ------ | ---------------------------------------- | ------------------------------------ |
| POST   | `/knowledge/documents`                   | Ingest or upsert a document          |
| GET    | `/knowledge/documents`                   | List document metadata               |
| GET    | `/knowledge/documents/{document_id}`     | Get one document                     |
| POST   | `/knowledge/documents/{document_id}/reindex` | Rebuild vectors from stored content |
| DELETE | `/knowledge/documents/{document_id}`     | Delete metadata and vectors          |
| POST   | `/knowledge/search`                      | Semantic search                      |

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

Save the `access_token` for subsequent requests.

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

### 4. Create an Itinerary

Manual itineraries still use `POST /itineraries/`. AI generation uses `POST /itineraries/{trip_id}/generate-ai`, which retrieves destination knowledge when available and then calls the original Claude itinerary composer.

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
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/               # use cases only
│   │   ├── auth.py
│   │   ├── trip.py
│   │   ├── itinerary.py
│   │   └── knowledge.py
│   ├── ai/                     # Claude and RAG
│   │   ├── llm/
│   │   └── rag/
│   └── controllers/
├── data/knowledge/           # sample travel guides
├── scripts/seed_knowledge.py
├── tests/
├── docker-compose.yml        # Postgres (host 5433) + Qdrant (6333)
├── .env.example
├── requirements.txt
└── README.md
```

### Database Management

```bash
# Reset Compose Postgres (destroys local Docker volume data)
docker compose down -v
docker compose up -d

# Reset SQLite
rm vacation_planner.db
```

### View Database Contents

```bash
# Compose Postgres (port 5433)
docker compose exec postgres psql -U vacation -d vacation_planner -c "SELECT * FROM users;"
docker compose exec postgres psql -U vacation -d vacation_planner -c "SELECT * FROM trips;"
docker compose exec postgres psql -U vacation -d vacation_planner -c "SELECT * FROM itineraries;"
docker compose exec postgres psql -U vacation -d vacation_planner -c "SELECT * FROM knowledge_documents;"

# SQLite
sqlite3 vacation_planner.db "SELECT * FROM users;"
sqlite3 vacation_planner.db "SELECT * FROM trips;"
sqlite3 vacation_planner.db "SELECT * FROM itineraries;"
sqlite3 vacation_planner.db "SELECT * FROM knowledge_documents;"
```
