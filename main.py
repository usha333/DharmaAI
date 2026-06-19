"""
main.py — FastAPI backend for DharmaAI.

This file wraps rag_core.py into a proper web API.
One endpoint: POST /guidance → takes a question, returns wisdom-based guidance.

Run with: uvicorn main:app --reload
Then test at: http://localhost:8000/docs (auto-generated Swagger UI)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time

# Import our RAG pipeline
from rag_core import get_guidance

# ── Create FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(
    title="DharmaAI",
    description="Wisdom-based life guidance using RAG over sacred texts",
    version="1.0.0"
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Without this, your Streamlit frontend (running on port 8501)
# can't talk to your FastAPI backend (running on port 8000)
# because browsers block cross-origin requests by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # in production, replace * with your actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request and Response Models ───────────────────────────────────────────────
# Pydantic models define exactly what shape the request/response JSON must be
# FastAPI uses these for automatic validation AND documentation

class GuidanceRequest(BaseModel):
    """What the user sends to the API"""
    message: str                        # the user's life situation
    user_name: Optional[str] = "Friend" # optional, for personalization

    class Config:
        # Example shown in the auto-generated /docs page
        json_schema_extra = {
            "example": {
                "message": "Someone came into my life unexpectedly but left without reason and I feel lost",
                "user_name": "Usha"
            }
        }

class GuidanceResponse(BaseModel):
    """What the API sends back"""
    category: str       # detected intent: career/relationship/family/stress/growth
    guidance: str       # the full structured wisdom response
    sources: list       # which texts were used: gita/mahabharata/meditations
    chunks_used: int    # how many text chunks were retrieved
    processing_time: float  # how long it took in seconds


# ── Health Check Endpoint ─────────────────────────────────────────────────────
# Always add a /health endpoint — it's how deployment platforms
# (Docker, Azure, AWS) know your service is alive
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "DharmaAI",
        "version": "1.0.0"
    }


# ── Root Endpoint ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "Welcome to DharmaAI — Wisdom-based Life Guidance",
        "docs": "/docs",
        "endpoints": {
            "guidance": "POST /guidance",
            "health": "GET /health"
        }
    }


# ── Main Guidance Endpoint ────────────────────────────────────────────────────
@app.post("/guidance", response_model=GuidanceResponse)
def get_wisdom_guidance(request: GuidanceRequest):
    """
    Main endpoint — takes a life situation, returns wisdom-based guidance.

    The pipeline:
    1. Validate input (FastAPI does this automatically via Pydantic)
    2. Call get_guidance() from rag_core.py
    3. Return structured response

    WHY POST and not GET?
    GET requests have URL length limits and shouldn't have a body.
    POST is correct for sending data that triggers processing.
    """

    # Validate message isn't empty or too short
    if not request.message or len(request.message.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Please describe your situation in at least 10 characters"
        )

    # Validate message isn't too long (protect against abuse)
    if len(request.message) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Please keep your message under 2000 characters"
        )

    # Track processing time — good for monitoring and showing users
    start_time = time.time()

    try:
        # Call our RAG pipeline from rag_core.py
        result = get_guidance(request.message)

        processing_time = round(time.time() - start_time, 2)

        return GuidanceResponse(
            category=result["category"],
            guidance=result["guidance"],
            sources=result["sources"],
            chunks_used=result["chunks_used"],
            processing_time=processing_time
        )

    except Exception as e:
        # If something goes wrong, return a proper HTTP error
        # Don't expose internal error details in production
        raise HTTPException(
            status_code=500,
            detail=f"Guidance generation failed: {str(e)}"
        )


# ── Categories Info Endpoint ──────────────────────────────────────────────────
# Nice to have — lets the frontend show users what categories exist
@app.get("/categories")
def get_categories():
    return {
        "categories": [
            {
                "id": "career",
                "label": "Career & Purpose",
                "description": "Work, job, direction, ambition, dharma"
            },
            {
                "id": "relationship",
                "label": "Relationships",
                "description": "Love, heartbreak, attachment, loneliness"
            },
            {
                "id": "family",
                "label": "Family",
                "description": "Parents, siblings, family conflict, expectations"
            },
            {
                "id": "stress",
                "label": "Stress & Anxiety",
                "description": "Overwhelm, fear, mental health, burnout"
            },
            {
                "id": "growth",
                "label": "Personal Growth",
                "description": "Self-improvement, meaning, spiritual seeking"
            }
        ]
    }


# ── Run directly for development ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # reload=True means server restarts automatically when you save the file
    # great for development, turn off in production
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)