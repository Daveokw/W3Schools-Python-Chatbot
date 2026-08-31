"""Streamlit interface for the lightweight Python Tutorial Chatbot."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from chatbot import Chatbot, Response, load_articles

APP_TITLE = "Python Tutorial Chatbot"
DATA_PATH = Path(__file__).resolve().parent / "data" / "knowledge_base.json"
WELCOME_MESSAGE = (
    "Ask me about Python fundamentals such as variables, collections, loops, "
    "functions, exceptions, classes, modules, files, or virtual environments."
)
SUGGESTED_QUESTIONS = (
    "What is a Python list?",
    "How do functions work?",
    "Explain list comprehensions",
    "What is the difference between a list and a tuple?",
)

st.set_page_config(page_title=APP_TITLE, page_icon="🐍", layout="centered")


@st.cache_resource(show_spinner=False)
def load_chatbot() -> Chatbot:
    """Load and index the bundled knowledge base once per app process."""
    return Chatbot(load_articles(DATA_PATH))


def reset_conversation() -> None:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE, "response": None}
    ]
    st.session_state.last_topic_slug = ""


def render_response(response: Response) -> None:
    st.markdown(response.answer)
    if response.example:
        st.code(response.example, language="python")
    if response.source_url:
        st.markdown(f"[Read the relevant Python documentation]({response.source_url})")
    if response.related_topics:
        st.caption("Related topics: " + ", ".join(response.related_topics))


def submit_question(chatbot: Chatbot, question: str) -> None:
    clean_question = " ".join(question.split())[:300]
    if not clean_question:
        return

    st.session_state.messages.append(
        {"role": "user", "content": clean_question, "response": None}
    )
    response = chatbot.answer(
        clean_question, context_slug=st.session_state.get("last_topic_slug", "")
    )
    if response.topic_slug:
        st.session_state.last_topic_slug = response.topic_slug
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "response": response.to_dict(),
        }
    )
    st.session_state.messages = st.session_state.messages[-20:]


try:
    chatbot = load_chatbot()
except (OSError, ValueError) as error:
    st.error("The tutorial knowledge base could not be loaded.")
    st.caption(str(error))
    st.stop()

st.title(APP_TITLE)
st.caption(
    "A lightweight, locally grounded guide to concepts covered by the official "
    "Python tutorial. No account, API key, or paid service is required."
)

with st.sidebar:
    st.header("About")
    st.write(
        "Answers are retrieved from a bundled knowledge base and linked to the "
        "official Python documentation. The app does not generate unsupported answers."
    )
    st.metric("Tutorial topics", len(chatbot.articles))
    st.button("Clear conversation", on_click=reset_conversation, use_container_width=True)

if "messages" not in st.session_state:
    reset_conversation()

if len(st.session_state.messages) == 1:
    st.subheader("Try a question")
    columns = st.columns(2)
    selected_question = None
    for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
        if columns[index % 2].button(
            suggestion, key=f"suggestion_{index}", use_container_width=True
        ):
            selected_question = suggestion
    if selected_question:
        submit_question(chatbot, selected_question)
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        response_data = message.get("response")
        if response_data:
            render_response(Response.from_dict(response_data))
        else:
            st.markdown(message["content"])

if question := st.chat_input("Ask a Python tutorial question", max_chars=300):
    submit_question(chatbot, question)
    st.rerun()
