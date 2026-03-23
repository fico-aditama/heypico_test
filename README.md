# HeyPico.ai - Fullstack Developer Code Test 2

This repository contains the solution for Code Test 2. It integrates a local LLM (via Ollama) with the Google Maps API (Places & Embed) to provide location recommendations with map directions and embedded UI maps.

## Architecture & Workflow

1. **Local LLM Orchestration**: The backend uses the `openai` Python API client to connect to a local Ollama instance (`http://localhost:11434/v1`). It leverages **Function Calling** (supported smoothly by `llama3.1` or equivalent models) to dynamically decide when to search for places based on the user's prompt.
2. **Backend API**: A `FastAPI` application (`main.py`) exposes the `/api/chat` endpoint to handle messages and serves a simple frontend (`index.html`) to demonstrate the interactive map embedding logic in real-time.
3. **Google Maps API**: 
   - `Text Search API` is used behind the scenes (invoked by the LLM Tool) to search for matching queries and fetch addresses + ratings.
   - `Maps Embed API` & `Search Links` are combined natively in the LLM's final response format, allowing the frontend to quickly render an iframe map or a direction hyperlink cleanly to the user.

## Assumptions & Best Practices Explained

1. **Security & Usage Limits Constraints**:
   - *Assumption*: To display an embedded map directly inside the chat UI (as requested by the requirement: "User should be able to view the location direction on the embedded map..."), the Google Maps API Key must be injected into the `<iframe>` URL. This makes it visible to the front-end client inspection.
   - *Best Practice (Security)*: To secure the key, this exact Maps API Key MUST be restricted in the **Google Cloud Console** using **HTTP referrers**. It should strictly allow only domains where the Web/UI app is hosted (e.g., `*.heypico.ai/*` or `http://localhost:8000/*`). This ensures the exposed key cannot be abused by a third party.
   - *Best Practice (Usage Limits)*: API quotas on the *Places API* must be limited in Google Cloud Controls (e.g., maximum 100 requests per day per project space) to prevent bad actors or runaway loops from causing billing overruns.

2. **Local LLM Setup**:
   - *Assumption*: The system assumes the user has installed and runs Ollama in localhost. The tool-calling mechanism handles logic locally without calling any cloud-based LLM (e.g., OpenAI or Anthropic).

## Getting Started

### 1. Prerequisites
- Python 3.9+ installed.
- [Ollama](https://ollama.com) installed and serving a function-calling enabled model (e.g., `llama3.1`).
- A valid Google Cloud account with a **Google Maps API Key**. Make sure to enable both the **Places API** and **Maps Embed API**.

### 2. Installation
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Update the `.env` file in the root folder with your details:

```ini
OLLAMA_BASE_URL="http://localhost:11434/v1"
OLLAMA_MODEL="llama3.1"
GOOGLE_MAPS_API_KEY="YOUR_ACTUAL_GOOGLE_MAPS_API_KEY"
```

### 4. Running the App
1. Make sure Ollama is running in the background. On a new terminal window run:
   ```bash
   ollama run llama3.1
   ```
2. Start the FastAPI backend server:
   ```bash
   uvicorn main:app --reload
   ```
3. Open `http://localhost:8000` in your favorite browser. 
4. Trigger the local AI by asking: *"Where is the best sushi place in Batam?"* or *"Cariin tempat ngopi buat WFC di Batam Centre"*
