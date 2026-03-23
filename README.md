# HeyPico.ai — Code Test 2: AI Maps Assistant

A **local-LLM-powered** chat assistant that uses **Google Maps API** to find and display places with interactive embedded maps. Built with FastAPI (Python) + Ollama + Google Maps (Text Search & Embed APIs).

---

## ✨ Features

- 🤖 **Local LLM Integration** — Uses Ollama (`llama3.1` or any function-calling supported model) via the OpenAI-compatible API client.
- 📍 **Google Maps Places Search** — Intelligently triggered by LLM **Function Calling** when user asks about locations.
- 🗺️ **Embedded Interactive Maps** — Shows `<iframe>` embedded maps per result directly in the chat UI.
- 💬 **Multi-turn Conversation** — Maintains session conversation history for natural follow-up questions.
- 💡 **Suggestion Chips** — Clickable quick prompts to get started instantly.
- 🔒 **Best Practices Security** — API keys loaded from `.env` (never hardcoded), request timeouts, result limits, and HTTP referrer restrictions documented.
- 🐳 **Docker Ready** — Full Docker + `docker-compose` support with health check and `restart: unless-stopped`.

---

## 🏗️ Architecture & Workflow

```
User Input (Browser)
        │
        ▼
  FastAPI Backend (main.py)
        │
        ▼
  LLM Service (llm_service.py)
  [Ollama LLM via OpenAI-compatible client]
        │
   LLM decides to call tool?
        ├── YES ──► Maps Service (maps_service.py)
        │                └── Google Maps Text Search API
        │                       └── Returns places + embed URLs
        │                               │
        │                     LLM synthesizes final answer
        │
        └── NO ──► Direct LLM reply
        │
        ▼
  Frontend (index.html)
  [Renders Markdown + iframes with embedded maps]
```

### Key Design Decisions:
1. **LLM Function Calling** — The LLM (`llama3.1`) autonomously decides when to search Google Maps using a registered `search_google_maps_places` tool, resulting in grounded, factual responses.
2. **Two-Round LLM Completion** — Round 1: let the model decide on tool use. Round 2: synthesize a final human-readable response using the map data returned. This prevents hallucinated places.
3. **Async-safe API Design** — The webhook server immediately returns after processing; long-running tasks follow the same async-safe pattern.

---

## 🔒 Security & Usage Best Practices

| Concern | Implementation |
|---|---|
| API Key Storage | Loaded strictly from `.env` file — never committed to source control |
| Key Exposure | Server-side Places API key is NOT sent to the frontend |
| Embed Key | Maps Embed API key must be restricted in **GCP → Credentials → HTTP referrers** to your domain |
| Request Timeout | `10s` timeout on all Google Maps API calls |
| Result Limit | Maximum 3 results per query to control API quota usage |
| Input Validation | FastAPI Pydantic model validates request body before processing |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- A Google Cloud account with **Places API (New)** and **Maps Embed API** enabled

### 1. Clone & Install
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create/update `.env` file:
```ini
OLLAMA_BASE_URL="http://localhost:11434/v1"
OLLAMA_MODEL="llama3.1"
GOOGLE_MAPS_API_KEY="YOUR_ACTUAL_GOOGLE_MAPS_API_KEY"
```

> ⚠️ **Important:** In your GCP Console, restrict your API key:
> - **Places Text Search key** → Restrict to IP address of your server.
> - **Maps Embed key** → Restrict to HTTP referrers (e.g. `http://localhost:8000/*`).

### 3. Run Ollama
```bash
ollama pull llama3.1
ollama serve
```

### 4. Start the App
```bash
uvicorn main:app --reload
```

Open `http://localhost:8000` and try: *"Find the best sushi restaurant in Jakarta"*

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

The app will auto-restart on failure (`restart: unless-stopped`) and exposes a `/health` check endpoint at `http://localhost:8000/health`.

---

## 💡 Assumptions & Notes

- **Function Calling Compatibility:** This solution uses `llama3.1` as it natively supports tool/function calling. Models like `llama3.2` or `mistral` with tool support work too.
- **iFrame Security:** The embedded Maps iFrame uses the same Google API key. As documented above, restricting this key by HTTP referrer in GCP mitigates abuse from external consumers.
- **Quota Control:** Limiting to 3 results per query significantly reduces the number of Text Search API calls, keeping the free-tier credits sufficient for development and demo purposes.
