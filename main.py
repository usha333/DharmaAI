"""
main.py — FastAPI backend for DharmaAI.

One main endpoint: POST /guidance
Accepts a message plus optional chat_history for conversation memory.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import time

from rag_core import get_guidance

app = FastAPI(
    title="DharmaAI",
    description="Wisdom-based life guidance using RAG over sacred texts",
    version="1.1.0"
)

# CORS — without this, Streamlit (port 8501) can't call FastAPI (port 8000)
# because browsers block cross-origin requests by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────
class ChatTurn(BaseModel):
    role: str       # "user" or "dharmaai"
    content: str

class GuidanceRequest(BaseModel):
    message: str
    user_name: Optional[str] = "Friend"
    chat_history: Optional[List[ChatTurn]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I feel stuck in my career",
                "user_name": "Usha",
                "chat_history": []
            }
        }

class GuidanceResponse(BaseModel):
    category: str
    guidance: str
    sources: list
    chunks_used: int
    processing_time: float


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "DharmaAI", "version": "1.1.0"}


@app.get("/")
def root():
    return {
        "message": "Welcome to DharmaAI — Wisdom-based Life Guidance",
        "docs": "/docs",
        "endpoints": {"guidance": "POST /guidance", "health": "GET /health"}
    }


# ── Main Endpoint ──────────────────────────────────────────────────────────────
@app.post("/guidance", response_model=GuidanceResponse)
def get_wisdom_guidance(request: GuidanceRequest):
    """
    Takes a message + conversation history, returns wisdom-based guidance.
    chat_history lets DharmaAI behave like an ongoing conversation.
    """
    if not request.message or len(request.message.strip()) < 1:
        raise HTTPException(status_code=400, detail="Please enter a message")

    if len(request.message) > 2000:
        raise HTTPException(status_code=400, detail="Message too long (max 2000 characters)")

    start_time = time.time()

    try:
        history_as_dicts = [
            {"role": turn.role, "content": turn.content}
            for turn in request.chat_history
        ]

        result = get_guidance(request.message, chat_history=history_as_dicts)
        processing_time = round(time.time() - start_time, 2)

        return GuidanceResponse(
            category=result["category"],
            guidance=result["guidance"],
            sources=result["sources"],
            chunks_used=result["chunks_used"],
            processing_time=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Guidance generation failed: {str(e)}")


@app.get("/categories")
def get_categories():
    return {
        "categories": [
            {"id": "career", "label": "Career & Purpose"},
            {"id": "relationship", "label": "Relationships"},
            {"id": "family", "label": "Family"},
            {"id": "stress", "label": "Stress & Anxiety"},
            {"id": "growth", "label": "Personal Growth"}
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
