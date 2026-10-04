# AI Vacation Planner - Backend API

## Overview

An intelligent vacation planning assistant backend API built with FastAPI. Users can register, manage trips and itineraries, ingest travel knowledge, speak or upload images, and ask an agent to generate itineraries using weather, maps, pricing, RAG, and MCP travel tools.

## Features

- **User Authentication**: JWT-based registration and login
- **Trip Management**: Create, read, update, and delete trips
- **Itinerary Planning**: Store day-by-day activities for each trip
- **Travel Knowledge Base**: Ingest, chunk, embed, and semantically search travel documents
- **Tool-using planner**: LangGraph agent that calls only the tools a request needs
- **Multimodal input/output**: Voice in, image in, spoken itinerary out
- **MCP travel tools**: Weather, maps, and a trip calendar exposed through Model Context Protocol
- **UUID Support**: Secure, non-sequential IDs for all entities
- **Production-Ready Architecture**: Controller-Service-Repository, with provider abstractions for LLM, embeddings, vector storage, and external APIs
- **API Documentation**: Automatic Swagger UI and ReDoc endpoints

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2
- **Database**: PostgreSQL (or SQLite for development)
- **Vector store**: Qdrant (in-memory store available for tests)
- **LLM**: Claude via `app/ai/llm` (Anthropic)
- **Embeddings**: OpenAI-compatible models for RAG only
- **Orchestration**: LangGraph
- **Speech**: OpenAI Whisper (STT) and OpenAI TTS, behind provider interfaces
- **Vision**: Claude image understanding
- **MCP**: In-process Model Context Protocol client/server for travel tools
- **Authentication**: JWT with bcrypt hashing
- **Validation**: Pydantic 2
- **Server**: Uvicorn

## Architecture

The project still uses the original layered flow. AI capabilities live under `app/ai/`; `app/services/` stays use-case orchestration.

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
docker compose up -d
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

## Phase 5: Frameworks & Orchestration

Phase 5 upgrades planning from a single retrieve-then-generate call into a tool-using agent.

**Before (Phase 4):**

```
Trip details → Retrieve travel knowledge → LLM response
```

**After (Phase 5):**

```
User request → Agent decides → Tool(s) run → LLM combines results → Response
```

### LLM integration

| Step | Component | Role |
| --- | --- | --- |
| Tool selection | LangChain `ChatAnthropic.bind_tools` | Claude decides which tools to call |
| Tool execution | `app/ai/tools` → `app/ai/providers` | Weather, maps, pricing, RAG; failures become warnings |
| Workflow | LangGraph `StateGraph` | `reason ⇄ tools → compose` |
| Final itinerary | Existing `LLMService` (`app/ai/llm`) | Same Claude prompts/parser, now with tool context |

The agent does **not** always run every tool. For *“Plan my Paris trip and include weather-friendly activities.”* it typically:

1. Loads trip details (destination, days, budget, style)
2. Calls the weather tool
3. Calls the RAG knowledge tool
4. Optionally maps/pricing if the request needs them
5. Composes the itinerary with those results

### Architecture updates

```
Controller (generate-ai or /planning/)
    ↓
PlanningService
    ↓
LangGraph agent
    ↓
Tool interface
    ↓
Weather / Maps / Pricing / Knowledge tools
    ↓
Providers or KnowledgeService
    ↓
LLMService (compose)
    ↓
ItineraryService persist
```

Swagger: http://localhost:8000/docs — tags **AI Planning** (`POST /planning/`) and **Itineraries** (`POST /itineraries/{trip_id}/generate-ai`).

## Phase 6: Multimodal AI & MCP

Phase 6 adds voice, images, spoken plans, and MCP without replacing the existing planner.

```
Text
Voice
Image
  ↓
Multimodal Processing
  ↓
Vacation Planner (PlanningService)
  ↓
LLM / Agent (LangGraph)
  ↓
Travel Tools through MCP
  ↓
Travel Plan  →  optional text-to-speech
```

### Multimodal architecture

| Mode | Flow |
| --- | --- |
| Speech-to-text | Audio → `SpeechToTextProvider` → transcribed text → existing `PlanningService` |
| Image | Image (+ optional text) → `VisionProvider` → extracted context → existing `PlanningService` |
| Text-to-speech | Existing plan text → `TextToSpeechProvider` → audio. The text response is kept. |
| Text planning | Unchanged `POST /planning/` and `POST /itineraries/{trip_id}/generate-ai` |

Voice and image never get a second planner. `MultimodalService` only prepares text, then calls `PlanningService.plan_trip`.

Provider interfaces live in `app/ai/providers/`:

- `SpeechToTextProvider` → OpenAI Whisper, or `fake` for tests
- `TextToSpeechProvider` → OpenAI TTS, or `fake` for tests
- `VisionProvider` → Claude vision, or `fake` for tests

Controllers never import provider SDKs.

### LLM integration

| Step | Component | Role |
| --- | --- | --- |
| Voice | OpenAI Whisper (`whisper-1`) | Turns audio into the traveler request |
| Image | Claude (`VISION_MODEL`, default `claude-haiku-4-5`) | Extracts destination, dates, hotels, maps, constraints |
| Tool selection | LangChain `ChatAnthropic.bind_tools` | Claude decides local tools and MCP tools |
| MCP | `InProcessMCPClient` → `TravelMCPServer` | `initialize`, `tools/list`, `tools/call` |
| Compose | Existing `LLMService` | Same Claude itinerary JSON as Phase 5 |
| Speech out | OpenAI TTS (`tts-1`) | Optional spoken plan |

Claude is initialized in `app/ai/llm/itinerary_generator.py` (compose) and `app/ai/providers/llm.py` (tool calling). Vision uses the same Anthropic account unless `VISION_API_KEY` is set.

### MCP integration

```
LLM / Agent
     │
     ▼
 MCP Client  (initialize / tools/list / tools/call)
     │
     ├── mcp_get_weather
     ├── mcp_search_places
     ├── mcp_add_calendar_event
     └── mcp_list_calendar_events
```

- **Server:** `app/ai/mcp/server.py` implements the MCP methods and optional FastMCP stdio (`python -m app.ai.mcp`).
- **Client:** `app/ai/mcp/client.py`. Default transport is in-process so the API does not spawn a subprocess per request.
- **Handlers:** `app/ai/mcp/handlers.py` reuse the existing weather and maps providers. Calendar is an in-process travel event store.
- **Adapter:** discovered MCP tools become `AgentTool` instances and are registered next to the original Phase 5 tools.
- Existing `get_weather` / `search_places` tools still work. MCP adds protocol-backed twins plus calendar.

| Tool | Input | Output |
| --- | --- | --- |
| `mcp_get_weather` | `location`, optional `days` | Forecast payload from the weather provider |
| `mcp_search_places` | `query`, optional `location`, `limit` | Places from the maps provider |
| `mcp_add_calendar_event` | `title`, `date`, optional `destination`, `notes` | Saved event |
| `mcp_list_calendar_events` | optional `destination` | Event list |

To add another MCP tool: define the JSON schema in `TOOL_SPECS`, implement a handler, and dispatch it in `TravelMCPServer._dispatch`. The agent picks it up on the next `tools/list`.

If MCP is down, planning continues with local tools and a warning.

## How to learn this project

Study one request through the layers. If you can narrate *“Plan my Paris trip and include weather-friendly activities”* from HTTP to Claude and back, you understand the system.

### Read in this order

1. `app/main.py` — routers
2. `app/core/dependencies.py` — JWT
3. `app/controllers/trip.py` + `app/services/trip.py` — simplest CRUD
4. `app/controllers/itinerary.py` — `generate-ai` is the product AI entry
5. `app/services/planning.py` — loads the trip, runs the graph, persists
6. `app/ai/agents/graph.py` — `reason` → `tools` → `compose`
7. `app/ai/tools/` + `app/ai/providers/` — agent never does HTTP itself
8. `app/services/knowledge.py` + `app/ai/rag/` — ingest and search
9. `app/ai/llm/` — existing Claude composer and JSON parser

`app/services/` is use cases. `app/ai/` is capabilities those use cases call.

### The path you should be able to draw

```
POST /itineraries/{trip_id}/generate-ai
    → PlanningService (load trip)
    → LangGraph
         reason  = Claude + bind_tools (should I call weather / RAG / maps / pricing?)
         tools   = only the tools the model requested; failures become warnings
         compose = existing LLMService + PromptBuilder + ResponseParser
    → ItineraryService.create_itinerary
    → { trip_id, itinerary, message }
```

`POST /planning/` is the same planner with `tools_used` and `warnings`. It does not require a trip.

### Why there are two Claude calls

- **Reason:** `ChatAnthropic` decides tools.
- **Compose:** `LLMService` writes the day-by-day JSON using the original prompts.

### How to practice

1. Draw `START → reason ⇄ tools → compose` on paper.
2. Read `tests/test_agent.py` (tool pick, skip tools, tool failure).
3. Trace `KnowledgeService.ingest_document` (hash, chunk, embed, Qdrant).
4. Open http://localhost:8000/docs and explain `generate-ai` vs `/knowledge/search` vs `/planning/`.

## Prerequisites

- Python 3.10 or higher (3.11 recommended; LangChain 1.x requires 3.10+)
- Docker Desktop (Postgres and Qdrant run in Compose; no local Postgres install needed)
- An Anthropic API key for itinerary generation, agent tool-calling, and image understanding
- An OpenAI key for speech-to-text and text-to-speech (`STT_PROVIDER=openai`, `TTS_PROVIDER=openai`)
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
| `OPENAI_API_KEY` | Shared OpenAI key for STT/TTS (and embeddings if needed) |
| `STT_PROVIDER` | `openai` or `fake` |
| `STT_API_KEY` | Optional STT key; falls back to `OPENAI_API_KEY` |
| `STT_MODEL` | Speech-to-text model (default `whisper-1`) |
| `STT_TIMEOUT` | Transcription timeout |
| `STT_MAX_BYTES` | Max audio upload size |
| `STT_ALLOWED_FORMATS` | Allowed audio extensions |
| `TTS_PROVIDER` | `openai` or `fake` |
| `TTS_API_KEY` | Optional TTS key; falls back to `OPENAI_API_KEY` |
| `TTS_MODEL` | Speech model (default `tts-1`) |
| `TTS_VOICE` | Voice name (default `alloy`) |
| `TTS_TIMEOUT` | Synthesis timeout |
| `VISION_PROVIDER` | `anthropic` or `fake` |
| `VISION_API_KEY` | Optional vision key; falls back to `ANTHROPIC_API_KEY` |
| `VISION_MODEL` | Vision-capable Claude model |
| `VISION_TIMEOUT` | Vision timeout |
| `VISION_MAX_BYTES` | Max image upload size |
| `VISION_ALLOWED_FORMATS` | Allowed image extensions |
| `MCP_ENABLED` | Discover MCP tools for the agent |
| `MCP_TRANSPORT` | `inprocess` (default), `fake`, or `stdio` |
| `MCP_TIMEOUT` | MCP call timeout |
| `MCP_SERVER_COMMAND` | Optional stdio server command |

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

Automated graph tests (tool selection, multi-tool execution, skipped tools, provider failure) are in `tests/test_agent.py`. API validation and error paths are in `tests/test_planning_api.py`. Multimodal and MCP coverage is in `tests/test_speech.py`, `tests/test_tts.py`, `tests/test_vision.py`, `tests/test_mcp.py`, and `tests/test_multimodal_api.py`.

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
| POST   | `/itineraries/{trip_id}/generate-ai/voice` | Transcribe audio, then the same planner |
| POST   | `/itineraries/{trip_id}/generate-ai/image` | Understand image, then the same planner |

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
| POST   | `/planning/voice` | Transcribe audio, then the same planner |
| POST   | `/planning/image` | Understand image + text, then the same planner |

### Multimodal

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST   | `/multimodal/speech-to-text` | Transcribe audio |
| POST   | `/multimodal/text-to-speech` | Speak itinerary text (`audio/mpeg` or JSON) |
| POST   | `/multimodal/vision` | Extract travel context from an image |
| POST   | `/multimodal/plan/voice` | Voice planning via `PlanningService` |
| POST   | `/multimodal/plan/image` | Image planning via `PlanningService` |

### MCP

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET    | `/mcp/tools` | Discover MCP travel tools |
| POST   | `/mcp/tools/{tool_name}` | Invoke an MCP tool |

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

Manual itineraries still use `POST /itineraries/`. AI generation uses `POST /itineraries/{trip_id}/generate-ai`, which runs the tool-using agent and then the original Claude itinerary composer. `POST /planning/` is the same planner with `tools_used` and `warnings`. Voice and image variants transcribe or extract context first, then call that same planner.

Voice planning:

```bash
curl -X POST "http://localhost:8000/planning/voice" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "audio=@request.wav;type=audio/wav" \
  -F "destination=Paris" \
  -F "days=4" \
  -F "include_speech=true"
```

Image planning:

```bash
curl -X POST "http://localhost:8000/planning/image" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "image=@eiffel.jpg;type=image/jpeg" \
  -F "message=Plan a 4-day trip around this destination" \
  -F "destination=Paris"
```

Speak a plan:

```bash
curl -X POST "http://localhost:8000/multimodal/text-to-speech" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "text=Day 1: Louvre and a Seine walk." \
  --output plan.mp3
```

Discover MCP tools:

```bash
curl -X GET "http://localhost:8000/mcp/tools" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
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
│   │   ├── knowledge.py
│   │   ├── planning.py
│   │   └── multimodal.py
│   ├── ai/                     # Claude, RAG, tools, agent, MCP
│   │   ├── llm/
│   │   ├── rag/
│   │   ├── providers/          # weather, maps, STT, TTS, vision
│   │   ├── tools/
│   │   ├── agents/
│   │   └── mcp/                # client, server, handlers, adapter
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
