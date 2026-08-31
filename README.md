# Python Tutorial Chatbot

A lightweight Streamlit chatbot that retrieves concise explanations and examples for concepts covered by the official Python tutorial.

[Open the live application](https://python-tutorial-chatbot.streamlit.app/)

## Overview

The application is a free portfolio prototype with no paid API, account, secret, external database, or runtime model download. It uses a bundled 40-topic knowledge base, weighted lexical retrieval, exact phrase matching, common synonym expansion, programming-symbol interpretation, and character-level typo tolerance to select a grounded response. When the available content does not support a question, it says so instead of inventing an answer.

## Features

- Conversational Streamlit chat interface with bounded session history
- Concise explanations and runnable Python examples
- Links to the relevant official Python tutorial pages
- Suggested questions and related-topic guidance
- Handling for greetings, help requests, minor spelling mistakes, and unsupported questions
- Recognition of common alternatives such as `array`, `hashmap`, `dict`, and `bool`
- Interpretation of symbols such as `[]`, `==`, `!=`, `//`, `%`, `*args`, and `**kwargs`
- Limited follow-up context for requests such as “explain more” or “show an example”
- Local knowledge loading with schema and source validation
- One lightweight runtime dependency and no external inference service
- Automated unit tests and Streamlit deployment checks
- Browser-based availability workflow for the deployed application

## Architecture

```text
User question
     |
     v
Input normalisation and tokenisation
     |
     v
Exact phrase + synonyms + symbols + weighted lexical + typo-tolerant ranking
     |
     +---- no reliable match ----> honest fallback response
     |
     v
Bundled tutorial article
     |
     v
Explanation + example + official documentation link
```

The retrieval engine is deterministic and runs entirely within the Streamlit process. It is intentionally not presented as a general-purpose generative AI system.

## Run locally

Python 3.10 or later is required.

```bash
git clone https://github.com/Daveokw/Python-Tutorial-Chatbot.git
cd Python-Tutorial-Chatbot
python -m venv .venv
python -m pip install -r requirements.txt
streamlit run app.py
```

Activate the virtual environment before installing dependencies when your development setup requires it.

## Knowledge base

Tutorial entries are stored in [`data/knowledge_base.json`](data/knowledge_base.json). Every entry contains a unique slug, title, search aliases, concise explanation, example, and official Python tutorial URL.

Validate the full knowledge base or try a command-line query with:

```bash
python embed_index.py
python embed_index.py --query "How do functions work?"
```

The legacy `embed_index.py` filename is retained for repository compatibility. It now validates and queries the local lexical index; neural embeddings are no longer required.

## Tests

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py chatbot.py embed_index.py
```

The tests cover knowledge validation, common questions, comparison questions, minor spelling mistakes, conversational messages, unsupported questions, and response serialisation.

## Streamlit deployment

Deploy `app.py` from the repository root. Streamlit Community Cloud installs the single pinned dependency from `requirements.txt`; no secrets or operating-system packages are required.

The GitHub Actions availability workflow checks the deployed interface every four hours and can request that Streamlit wake a sleeping application. Scheduled workflows are best-effort and cannot guarantee that a free Community Cloud application will never hibernate.

## Limitations

- The chatbot covers 40 curated Python tutorial topics rather than every Python library or advanced topic.
- Retrieval is lexical and deterministic, not a semantic embedding or large-language-model pipeline.
- Follow-up context is deliberately limited to the most recently matched topic and does not provide general conversational reasoning.
- Answers are educational summaries and should be checked against the linked documentation when version-specific behaviour matters.
- Conversation history exists only in the current Streamlit session.

## Sources

The educational entries are original summaries linked to the [official Python tutorial](https://docs.python.org/3/tutorial/). Python documentation is maintained by the Python Software Foundation and its contributors.
