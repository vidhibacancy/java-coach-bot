"""
FastAPI backend for the Java Interview Coach, serving the static
frontend in static/ and exposing the question-bank/chat operations from
bot_core.InterviewBot as JSON endpoints.

Run:
    uvicorn server:app --reload
Then open http://127.0.0.1:8000
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if not os.environ.get("GOOGLE_API_KEY"):
    sys.exit(
        "GOOGLE_API_KEY is not set.\n"
        "Either put it in a .env file next to server.py (GOOGLE_API_KEY=your-key-here)\n"
        "or set it in your shell before starting the server, e.g. (PowerShell):\n"
        '  $env:GOOGLE_API_KEY = "your-key-here"\n'
        "then run: uvicorn server:app --reload"
    )

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from bot_core import InterviewBot

app = FastAPI(title="Java Interview Coach")
bot = InterviewBot()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@app.get("/api/status")
def api_status():
    return {"question_count": len(bot.question_bank)}


@app.get("/api/topics")
def api_topics():
    topics = sorted({q["topic"] for q in bot.question_bank})
    return {"topics": topics}


@app.get("/api/questions")
def api_questions(topic: str | None = None, query: str | None = None):
    if topic:
        matches = [q for q in bot.question_bank if q["topic"] == topic]
    elif query:
        matches = bot.find_questions(query, k=8)
    else:
        raise HTTPException(status_code=400, detail="topic or query is required")
    return {
        "questions": [
            {"id": q["id"], "question": q["question"], "difficulty": q["difficulty"], "topic": q["topic"]}
            for q in matches
        ]
    }


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    history = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in req.history
    ]
    result = bot.chat(req.message, history)
    return {
        "reply": result["answer"],
        "confidence": result["confidence"],
        "sources": result["sources"],
    }


# Must be mounted last: it's registered as a catch-all "/" route, and
# Starlette matches routes in registration order, so the /api/* routes
# above need to be added first or the mount would shadow them.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
