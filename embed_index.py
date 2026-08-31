"""Validate or query the lightweight knowledge index from the command line.

The filename is retained for compatibility with the original repository. The app no
longer builds neural embeddings because its bundled lexical index is faster and more
appropriate for a small Streamlit demonstration.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from chatbot import Chatbot, load_articles

DATA_PATH = Path(__file__).resolve().parent / "data" / "knowledge_base.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query", help="Run a sample question against the validated knowledge base."
    )
    arguments = parser.parse_args()

    chatbot = Chatbot(load_articles(DATA_PATH))
    print(f"Validated {len(chatbot.articles)} tutorial topics from {DATA_PATH}.")

    if arguments.query:
        response = chatbot.answer(arguments.query)
        print(f"\n{response.answer}")
        if response.example:
            print(f"\n{response.example}")
        if response.source_url:
            print(f"\nSource: {response.source_url}")


if __name__ == "__main__":
    main()
