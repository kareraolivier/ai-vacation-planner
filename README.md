# AI Vacation Planner - Backend API

## Overview

An intelligent vacation planning assistant backend API built with FastAPI. Users can register, manage trips and itineraries, ingest travel knowledge, and ask an agent to generate itineraries using weather, maps, pricing, and RAG tools.

## Features

- **User Authentication**: JWT-based registration and login
- **Trip Management**: Create, read, update, and delete trips
- **Itinerary Planning**: Store day-by-day activities for each trip
- **Travel Knowledge Base**: Ingest, chunk, embed, and semantically search travel documents
- **Tool-using planner**: LangGraph agent that calls only the tools a request needs
- **UUID Support**: Secure, non-sequential IDs for all entities
- **Production-Ready Architecture**: Controller-Service-Repository, with provider abstractions for LLM, embeddings, vector storage, and external APIs
- **API Documentation**: Automatic Swagger UI and ReDoc endpoints

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2
- **Database**: PostgreSQL (or SQLite for development)
- **Vector store**: Qdrant (in-memory store available for tests)
- **LLM**: Claude via the existing `app/llm` layer (Anthropic)
- **Embeddings**: OpenAI-compatible models for RAG only
- **Orchestration**: LangGraph
- **Authentication**: JWT with bcrypt hashing
- **Validation**: Pydantic 2
- **Server**: Uvicorn

## Architecture

The project still uses the original layered flow. RAG and agents were added inside `app/services/` rather than as a second application.

```
Controllers (HTTP layer)
    ↓
Services (Business logic, RAG, tools, agent)
    ↓
Repositories (Data access)
    ↓
Models (Database schema)
```

```
User request
    ↓
PlanningService
    ↓
LangGraph agent
    ↓
Tool interface (weather / maps / pricing / knowledge)
    ↓
Provider or KnowledgeService
    ↓
Compose itinerary with the LLM
    ↓
Optional persist via existing ItineraryService
```

- **Controllers**: HTTP, validation, authentication
- **Services**: Business logic, RAG pipeline, tool orchestration
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
ranked chunks for API clients or the knowledge tool
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
docker compose up -d qdrant
```

For unit tests, `VECTOR_STORE_PROVIDER=memory` uses cosine search in process.

### LangChain and LangGraph

LangChain is used where it replaces code we would otherwise write ourselves:

- `RecursiveCharacterTextSplitter` for chunking
- `ChatAnthropic` for tool selection (same Claude account as `LLMService`)
- `OpenAIEmbeddings` only when `EMBEDDING_PROVIDER=openai`
- `StructuredTool` so the agent sees names, descriptions, and input schemas

LangGraph owns the planning workflow. The graph is a `StateGraph` with three nodes:

1. **reason** — tool-calling model decides whether weather, maps, pricing, or knowledge is needed
2. **tools** — executes only the requested tools; provider errors become warnings
3. **compose** — second LLM call builds the day-by-day itinerary from trip constraints plus tool results

```
START → reason ─┬─(tool calls)→ tools → reason
                └─(done / max iterations)→ compose → END
```

Additional tools can be registered in `ToolRegistry` without changing the graph.

### Agent and tools

```
Agent
  ↓
Tool interface (AgentTool)
  ↓
WeatherTool / MapsTool / PricingTool / KnowledgeTool
  ↓
WeatherService-style provider / KnowledgeService
  ↓
Open-Meteo, Nominatim, configured pricing HTTP API, or vector retrieval
```

| Tool | Name | When the agent should use it |
| --- | --- | --- |
| Weather | `get_weather` | Weather, outdoor plans, packing, seasonal timing |
| Maps | `search_places` | Places, coordinates, nearby attractions |
| Pricing | `estimate_pricing` | Budget or cost questions |
| Knowledge | `search_travel_knowledge` | Guides, tips, hidden gems, FAQs, destination notes |

The agent does not call every tool on every request. If a provider is down, that tool returns a structured failure and planning continues.

## Prerequisites

- Python 3.10 or higher (3.11 recommended; LangChain 1.x requires 3.10+)
- PostgreSQL (optional — SQLite works for development)
- Qdrant if you use the default vector store
- An Anthropic API key for itinerary generation and agent tool-calling
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

### 5. Database and Qdrant

PostgreSQL:

```bash
createdb vacation_planner
```

SQLite: set `DATABASE_URL=sqlite:///./vacation_planner.db`.

Qdrant:

```bash
docker compose up -d qdrant
```

Tables are created on startup via SQLAlchemy `create_all`.

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
| `ANTHROPIC_API_KEY` | Claude API key used by `LLMService` and the agent |
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
| `AGENT_MAX_TOOL_ITERATIONS` | Safety cap on tool loops |
| `WEATHER_PROVIDER` | Weather provider (`openmeteo`) |
| `WEATHER_API_URL` | Forecast API base URL |
| `WEATHER_GEOCODE_URL` | Geocoding API base URL |
| `WEATHER_API_KEY` | Optional weather key |
| `MAPS_PROVIDER` | Maps provider (`nominatim`) |
| `MAPS_API_URL` | Maps API base URL |
| `MAPS_API_KEY` | Optional maps key |
| `MAPS_USER_AGENT` | Required by Nominatim |
| `PRICING_PROVIDER` | Pricing provider (`http`) |
| `PRICING_API_URL` | Live pricing endpoint; if empty, the pricing tool fails softly |
| `PRICING_API_KEY` | Optional pricing key |

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

## How to test the agent workflow

Example request:

```bash
curl -X POST "http://localhost:8000/planning/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Plan my Paris trip and include weather-friendly activities.",
    "destination": "Paris",
    "days": 4,
    "budget": 1500,
    "trip_style": "budget"
  }'
```

To persist onto an existing trip, pass `trip_id` (and keep `persist_itinerary` true). The saved payload uses the existing itinerary schema: `{ trip_id, itinerary, message }`.

The response includes `tools_used` and `warnings` so you can see whether the model called weather, RAG, maps, or pricing. A weather-focused Paris request should typically call `get_weather` and `search_travel_knowledge`, not every tool.

Automated graph tests (tool selection, multi-tool execution, skipped tools, provider failure) are in `tests/test_agent.py`. API validation and error paths are in `tests/test_planning_api.py`.

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
| POST   | `/itineraries/{trip_id}/generate-ai` | Claude + optional tools/RAG, then save |

### Knowledge Base

| Method | Endpoint                                 | Description                          |
| ------ | ---------------------------------------- | ------------------------------------ |
| POST   | `/knowledge/documents`                   | Ingest or upsert a document          |
| GET    | `/knowledge/documents`                   | List document metadata               |
| GET    | `/knowledge/documents/{document_id}`     | Get one document                     |
| POST   | `/knowledge/documents/{document_id}/reindex` | Rebuild vectors from stored content |
| DELETE | `/knowledge/documents/{document_id}`     | Delete metadata and vectors          |
| POST   | `/knowledge/search`                      | Semantic search                      |

### AI Planning

| Method | Endpoint      | Description                                      |
| ------ | ------------- | ------------------------------------------------ |
| POST   | `/planning/`  | Run the tool-using agent and return an itinerary |

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

Manual itineraries still use `POST /itineraries/`. AI generation uses the existing `POST /itineraries/{trip_id}/generate-ai` endpoint, which now runs the tool-using agent and then the original Claude itinerary composer. `POST /planning/` is the same planner with a richer response (`tools_used`, `warnings`) and does not require a trip.

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
│   ├── services/
│   │   ├── auth.py
│   │   ├── trip.py
│   │   ├── itinerary.py
│   │   ├── knowledge.py
│   │   ├── planning.py
│   │   ├── rag/              # loader, chunker, embeddings, vector store, retriever
│   │   ├── providers/        # weather, maps, pricing, LLM
│   │   ├── tools/            # agent-facing tool wrappers
│   │   └── agents/           # LangGraph state and graph
│   └── controllers/
├── data/knowledge/           # sample travel guides
├── scripts/seed_knowledge.py
├── tests/
├── docker-compose.yml        # local Qdrant
├── .env.example
├── requirements.txt
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
psql -d vacation_planner -c "SELECT * FROM knowledge_documents;"

# SQLite
sqlite3 vacation_planner.db "SELECT * FROM users;"
sqlite3 vacation_planner.db "SELECT * FROM trips;"
sqlite3 vacation_planner.db "SELECT * FROM itineraries;"
sqlite3 vacation_planner.db "SELECT * FROM knowledge_documents;"
```
