"""
Core logic for the Java Interview Question Bot.

Loads the question bank, builds two vector stores, and exposes the
practice / chat operations as a single InterviewBot class. Shared by the
CLI (bot.py) and the web UI (server.py) so there's one place that talks
to the LLM and the question bank.

Two separate indexes, two separate jobs:
  - question index  (topic + question text, one doc per question)
      -> used to FIND questions (topic browsing / semantic question search)
  - knowledge index  (question+explanation+follow-up chunks, PLUS
    concepts.md chunked by heading) -> used to GROUND chat answers (RAG)
"""

import os
import re
import json
import logging
import hashlib

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.getLogger("google_genai.models").setLevel(logging.ERROR)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "questions.json")
CONCEPTS_PATH = os.path.join(os.path.dirname(__file__), "data", "concepts.md")
EMBEDDING_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache", "embeddings.json")


class CachedEmbeddings(Embeddings):
    """Wraps an embeddings model with a local on-disk cache keyed by content
    hash, so re-embedding the same question bank on every restart doesn't
    burn API quota - only genuinely new/changed text triggers a real call."""

    def __init__(self, embeddings, cache_path, model_name):
        self._embeddings = embeddings
        self._cache_path = cache_path
        self._model_name = model_name
        self._cache = self._load()

    def _load(self):
        if os.path.exists(self._cache_path):
            with open(self._cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
        with open(self._cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f)

    def _key(self, text):
        # Namespaced by model so switching embedding models never mixes
        # vectors from two different embedding spaces in the same cache.
        return hashlib.sha256(f"{self._model_name}::{text}".encode("utf-8")).hexdigest()

    def embed_documents(self, texts):
        vectors = [None] * len(texts)
        missing_texts, missing_indices = [], []

        for i, text in enumerate(texts):
            cached = self._cache.get(self._key(text))
            if cached is not None:
                vectors[i] = cached
            else:
                missing_texts.append(text)
                missing_indices.append(i)

        if missing_texts:
            fresh = self._embeddings.embed_documents(missing_texts)
            for idx, text, vector in zip(missing_indices, missing_texts, fresh):
                vectors[idx] = vector
                self._cache[self._key(text)] = vector
            self._save()

        return vectors

    def embed_query(self, text):
        key = self._key(text)
        if key in self._cache:
            return self._cache[key]
        vector = self._embeddings.embed_query(text)
        self._cache[key] = vector
        self._save()
        return vector

SYSTEM_MESSAGE = SystemMessage(content=(
    "You are a Java interview prep coach that answers ONLY using the CONTEXT "
    "given in each message, retrieved from a fixed question bank. Do not use "
    "outside knowledge, even if you know the answer. If the context doesn't "
    "contain enough to answer, say so plainly instead of guessing. Give a "
    "complete, well-explained answer - don't pad it with fluff, but don't cut "
    "it short either. Always respond with exactly the JSON shape requested in "
    "the message - no markdown code fences, no extra text before or after it."
))

PRACTICE_PROMPT = """You are an interview prep assistant for a Java developer.
Below are real questions retrieved from the question bank based on the user's request.
Present them as a short numbered list (just the question text, not the explanation).
If the retrieved questions don't seem relevant to what the user asked, say so honestly
instead of forcing a connection.

User request: {request}

Retrieved questions:
{questions}
"""

RAG_ANSWER_TEMPLATE = """Context retrieved from the interview question bank:
---
{context}
---

Answer the question below using ONLY the context above - do not use outside \
knowledge. If the context does not answer it, say so plainly in the answer field.

Respond with a single valid JSON object and nothing else, in exactly this shape:
{{"answer": "<your answer, written naturally - never mention \\"context\\" or \\"retrieved\\">", "confidence": <float 0.0-1.0, how well the context supports this answer - 0.0 if not covered>}}

User question: {question}"""

def get_text(response):
    """Return plain text from an LLM response, handling both string and
    list-of-content-block shapes."""
    content = response.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def parse_json_answer(text):
    """Parse the {"answer", "confidence"} JSON the RAG prompt asked for,
    tolerating stray code-fence markers some models add around it."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        confidence = float(data.get("confidence", 0.0))
        return {"answer": str(data.get("answer", "")).strip(), "confidence": confidence}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"answer": text.strip(), "confidence": 0.0}


def load_concept_sections(path):
    """Split a Markdown file into (heading, body) sections on '## ' headings,
    structure-aware chunking (like splitting a book by chapter) rather than
    blindly cutting by character count. Returns a Document per section."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    # parts = [text-before-first-heading, heading1, body1, heading2, body2, ...]
    sections = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip()
        if body:
            sections.append(
                Document(page_content=body, metadata={"topic": heading, "source": "concepts.md"})
            )
    return sections


class InterviewBot:
    def __init__(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            self.question_bank = json.load(f)

        self.questions_by_id = {q["id"]: q for q in self.question_bank}

        self.llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.5)
        embedding_model = "models/gemini-embedding-2"
        embeddings = CachedEmbeddings(
            GoogleGenerativeAIEmbeddings(model=embedding_model),
            EMBEDDING_CACHE_PATH,
            embedding_model,
        )

        # --- Question index: for finding questions (topic browsing / search) ---
        docs = [
            Document(
                page_content=f"Topic: {q['topic']}. Question: {q['question']}",
                metadata={"id": q["id"], "difficulty": q["difficulty"], "topic": q["topic"]},
            )
            for q in self.question_bank
        ]

        self.vector_store = InMemoryVectorStore(embeddings)
        self.vector_store.add_documents(docs)
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})

        # --- Knowledge index: chunked question+explanation, for grounding chat answers (RAG) ---
        knowledge_docs = [
            Document(
                page_content=(
                    f"Question: {q['question']}\n"
                    f"Explanation: {q['explanation']}\n"
                    f"Follow-up: {q['follow_up']}"
                ),
                metadata={"id": q["id"], "difficulty": q["difficulty"], "topic": q["topic"]},
            )
            for q in self.question_bank
        ]

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
        knowledge_chunks = splitter.split_documents(knowledge_docs)

        # --- Concept document: general Java/Spring Boot knowledge, chunked by
        # heading first (structure-aware), then by size within each section ---
        if os.path.exists(CONCEPTS_PATH):
            concept_sections = load_concept_sections(CONCEPTS_PATH)
            knowledge_chunks += splitter.split_documents(concept_sections)

        self.knowledge_store = InMemoryVectorStore(embeddings)
        self.knowledge_store.add_documents(knowledge_chunks)
        self.knowledge_retriever = self.knowledge_store.as_retriever(search_kwargs={"k": 4})

    def find_questions(self, user_request, k=3):
        self.retriever.search_kwargs["k"] = k
        matches = self.retriever.invoke(user_request)
        return [self.questions_by_id[doc.metadata["id"]] for doc in matches]

    def practice(self, user_request):
        matches = self.find_questions(user_request)
        questions_text = "\n".join(
            f"- {q['question']} ({q['topic']}, {q['difficulty']})" for q in matches
        )
        prompt = PRACTICE_PROMPT.format(request=user_request, questions=questions_text)
        return get_text(self.llm.invoke(prompt)), matches

    def chat(self, user_message, history):
        """history is a list of HumanMessage/AIMessage (unaugmented - the plain
        answer text, not the RAG-augmented prompt or JSON built here). Returns
        {"answer": str, "confidence": float, "sources": [topic, ...]}. Caller is
        responsible for appending the ORIGINAL user_message and result["answer"]
        (not the augmented prompt or raw JSON) to history.

        Retrieves relevant chunks from the knowledge index and injects them into
        this turn's message only, so grounding context never pollutes stored history.
        """
        chunks = self.knowledge_retriever.invoke(user_message)
        context = "\n\n".join(c.page_content for c in chunks) if chunks else "(none found)"
        augmented_message = RAG_ANSWER_TEMPLATE.format(context=context, question=user_message)

        messages = [SYSTEM_MESSAGE] + history + [HumanMessage(content=augmented_message)]
        response = self.llm.invoke(messages)
        parsed = parse_json_answer(get_text(response))

        answer = parsed["answer"] or "I don't have information on that in the question bank."
        confidence = max(0.0, min(1.0, parsed["confidence"]))

        sources = []
        if confidence >= 0.4:
            seen = set()
            for c in chunks:
                topic = c.metadata.get("topic")
                if topic and topic not in seen:
                    seen.add(topic)
                    sources.append(topic)

        return {"answer": answer, "confidence": round(confidence, 2), "sources": sources}
