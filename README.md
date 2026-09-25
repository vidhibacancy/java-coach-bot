# Interview Question Similarity Bot

A domain-specific chatbot that helps a Java developer practice for interviews.
It has two ways to interact with it:

1. **Question Bank browsing** — pick a topic (or type a custom search), see
   the real questions under it, click one to ask it directly.
2. **Direct chat** — ask any Java or Spring Boot question and get an answer
   grounded via retrieval-augmented generation (RAG) in two knowledge
   sources: a curated 50-question bank (`data/questions.json`) and a
   general concepts document (`data/concepts.md`) — with a confidence score
   and cited source topics.

## Why this approach

A generic LLM call ("give me a Java multithreading question") produces a
plausible-sounding but random question every time, with no guarantee of
quality, and no consistent reference to answer against. This bot instead:

- Retrieves real, vetted questions from a fixed bank by **semantic
  similarity**, so "I'm weak in concurrency" correctly matches
  "Multithreading" questions even though the wording differs.
- Grounds every chat answer in the bank's own curated explanations via RAG,
  instead of letting the model answer purely from its own (unverifiable)
  training knowledge.

## Architecture

```
data/questions.json                              data/concepts.md
(50 questions: topic,                          (22 sections, one per
 difficulty, explanation,                       '## Heading', general Java
 follow-up)                                     & Spring Boot concepts)
        |                                                |
        v                                                v
  one Document per question                    split on '## ' headings into
  (question+explanation+follow-up)              one Document per section
        |                                                |
        +-------------------+      +---------------------+
                            |      |
                            v      v
              RecursiveCharacterTextSplitter
              (chunk_size=500, overlap=80)
              -> 118 question chunks + 64 concept chunks = 182 total
                            |
                            v
       Gemini embeddings (gemini-embedding-2, cached to disk)
                            |
                            v
                 Knowledge index (InMemoryVectorStore)
                            |
                            v
              used to GROUND chat answers (RAG):
               - embed the user's message
               - retrieve top-4 chunks (from either source)
               - inject as context into the prompt (this turn
                 only - never stored in chat history)
                            |
                            v
          Gemini (gemini-3.1-flash-lite) answers ONLY from
          that context, as strict JSON:
          {"answer": "...", "confidence": 0.0-1.0}
                            |
                            v
          Sources (topics of the retrieved chunks) attached
          if confidence >= 0.4

---------------------------------------------------------------

data/questions.json (separately, unchunked)
        |
        v
  one Document per question (topic + question text only)
        |
        v
  Gemini embeddings -> Question index (InMemoryVectorStore)
        |
        v
  used to FIND questions:
   - GET /api/topics
   - GET /api/questions?topic=X (exact filter)
   - GET /api/questions?query=X (semantic search)
        |
        v
  click a question -> asked as a normal chat message (see above)
```

This mirrors the classic RAG pipeline (loader → splitter → embeddings →
vector store → retriever → grounded generation). `concepts.md` is split
**structure-aware first** (by Markdown heading, so each section stays
topically whole) and only then chunked by size — the same two-stage
approach used for PDF/Markdown sources in typical RAG systems, rather than
blindly cutting by character count from the start. The question index is
kept separate and unchunked, since it exists purely to find/browse
questions, not to answer them.

### Embedding cache

Every restart would otherwise re-embed all 50 questions + 182 knowledge
chunks, burning API quota for no reason since the data rarely changes.
`bot_core.py` wraps the embeddings model in `CachedEmbeddings`, which
stores every vector in `.cache/embeddings.json`, keyed by a hash of
`(model name, text)`. Only genuinely new or changed text triggers a real
API call after the first run.

## Setup

```bash
pip install -r requirements.txt
```

Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/).

### Web UI (recommended)

A FastAPI backend (`server.py`) serves the question bank as JSON endpoints,
with a custom HTML/CSS/JS chat frontend in `static/`. Conversations persist
per-browser (localStorage), with a sidebar to switch between them.

```bash
# put your key in a .env file next to server.py...
echo GOOGLE_API_KEY=your-key-here > .env
# ...or set it in your shell instead, e.g. (PowerShell):
#   $env:GOOGLE_API_KEY = "your-key-here"

uvicorn server:app --reload
```

Then open **http://127.0.0.1:8000**. If port 8000 is already in use on your
machine, run `uvicorn server:app --reload --port 8001` instead and open that
port.

### CLI

```bash
python bot.py
```

You'll be prompted for the key interactively; it's stored only in the
session environment, never written to disk.

## API endpoints (web UI backend)

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | Question count loaded |
| `GET /api/topics` | List of distinct topics |
| `GET /api/questions?topic=X` | Exact-match questions under a topic |
| `GET /api/questions?query=X` | Semantic search for questions matching free text |
| `POST /api/chat` | `{message, history}` → `{reply, confidence, sources}` (RAG-grounded) |

## Usage

**Question Bank (web UI):** click "Question Bank" in the sidebar → pick a
topic → pick one of its real questions → it's asked directly in chat, no
list dump.

**Direct chat (web UI or CLI):**
```
You: What is a functional interface?
AI: A functional interface is an interface that contains exactly one
    abstract method. It may optionally be marked with @FunctionalInterface
    and can also include default or static methods.
    (Sources: Java 8+ Features, OOP & Core Java | Confidence: 1.0)
```
If the question bank doesn't cover something, the bot says so instead of
guessing from outside knowledge.

## Extending this

- Add more questions to `data/questions.json`, or more sections (`## Heading`)
  to `data/concepts.md` — no code changes needed either way (the embedding
  cache only re-embeds what's new).
- Swap `InMemoryVectorStore` for a real vector database (Qdrant, Chroma,
  pgvector) if the bank grows large enough that brute-force search becomes
  slow, or if you need persistence/multi-process access.
- Add hybrid search (dense + BM25 sparse, fused via RRF) for better recall
  on keyword-heavy queries, similar to a Qdrant-based hybrid setup.
- Persist conversations server-side (instead of localStorage) if you need
  them to follow you across browsers/devices.

## Tech stack

Python, LangChain (`langchain-core`, `langchain-text-splitters`,
`langchain-google-genai`), Gemini (`gemini-3.1-flash-lite` for chat/RAG
generation, `gemini-embedding-2` for embeddings), `InMemoryVectorStore` with
a disk-backed embedding cache, FastAPI + vanilla HTML/CSS/JS frontend — zero
external infrastructure (no database or Docker required).
