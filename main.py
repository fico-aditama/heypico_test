from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

from llm_service import get_llm_response
from vector_memory import add_memory, get_recent_history, clear_vector_db

app = FastAPI(title="HeyPico AI Maps Assistant", version="1.0.0")

# Allow all origins for local dev / Docker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        # Add user's message to RAG Vector DB Memory
        add_memory("user", req.message)
        
        # We don't need to pass history from the frontend anymore!
        # The backend fetches it natively from Vector DB now.
        response_text = get_llm_response(req.message)
        
        # Add Assistant reply to Vector Memory
        add_memory("assistant", response_text)
        
        return {"reply": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")

@app.get("/api/history")
async def fetch_history():
    """Endpoint for frontend to render past chat sessions from Vector DB."""
    return {"history": get_recent_history()}

@app.delete("/api/history")
async def wipe_history():
    """Clear the Vector DB memory."""
    clear_vector_db()
    return {"status": "success"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "model": os.getenv("OLLAMA_MODEL", "llama3.1")}

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
