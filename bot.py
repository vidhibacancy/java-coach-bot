"""
Interview Question Similarity Bot (CLI)
----------------------------------------
A domain-specific chatbot that helps Java developers practice for interviews.

Architecture (same pipeline as the workshop, applied to a new domain):
  Question bank (JSON) -> Documents -> Embeddings -> InMemoryVectorStore
    -> Retriever (semantic similarity) -> LLM (practice / explain)

Practice mode - "give me questions on X" -> retrieves similar questions.
Anything else is treated as normal chat with memory of this session.

For the web UI, run `uvicorn server:app --reload` instead.

Run:
    python bot.py
"""

import os
from getpass import getpass

from langchain_core.messages import HumanMessage, AIMessage

if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass("Enter your Gemini API key: ")

from bot_core import InterviewBot

HELP_TEXT = """
Commands:
  practice <topic>     e.g. "practice multithreading" - lists similar questions
  help                 show this message
  quit                 exit

Anything else is treated as normal chat with memory of this session.
"""


def main():
    print("=== Interview Question Similarity Bot ===")
    print(f"Loading question bank into the vector store...")
    bot = InterviewBot()
    print(f"Loaded {len(bot.question_bank)} interview questions. Ready.\n")
    print(HELP_TEXT)

    conversation_history = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "help":
            print(HELP_TEXT)
            continue

        lower = user_input.lower()
        if lower.startswith("practice"):
            topic = user_input[len("practice"):].strip() or "general Java"
            reply, matches = bot.practice(topic)
            print("\nAI:", reply, "\n")
        else:
            result = bot.chat(user_input, conversation_history)
            reply = result["answer"]
            conversation_history.append(HumanMessage(content=user_input))
            conversation_history.append(AIMessage(content=reply))
            print("\nAI:", reply)
            if result["sources"]:
                print(f"(Sources: {', '.join(result['sources'])} | Confidence: {result['confidence']})")
            print()


if __name__ == "__main__":
    main()
