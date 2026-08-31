"""Dependency-free retrieval engine for the Python Tutorial Chatbot."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_+-]*")
SPACE_PATTERN = re.compile(r"\s+")
STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "explain",
    "for",
    "how",
    "in",
    "is",
    "me",
    "of",
    "on",
    "please",
    "python",
    "show",
    "tell",
    "the",
    "to",
    "use",
    "what",
    "when",
    "with",
    "work",
    "works",
}
SYMBOL_ALIASES = (
    ("**kwargs", " keyword arguments "),
    ("*args", " positional arguments "),
    ("==", " equality comparison "),
    ("!=", " not equal comparison "),
    ("//", " floor division "),
    ("**", " exponentiation "),
    ("[]", " list "),
    ("{}", " dictionary set "),
    ("%", " modulo remainder "),
)
TOKEN_ALIASES = {
    "arrays": "list",
    "array": "list",
    "bool": "boolean",
    "classes": "class",
    "dict": "dictionary",
    "dicts": "dictionary",
    "dictionaries": "dictionary",
    "errors": "exception",
    "functions": "function",
    "hashmap": "dictionary",
    "hashmaps": "dictionary",
    "integers": "integer",
    "lists": "list",
    "loops": "loop",
    "modules": "module",
    "objects": "object",
    "sets": "set",
    "strings": "string",
    "tuples": "tuple",
}
GREETING_INPUTS = {"hello", "hey", "hi", "good morning", "good afternoon"}
THANKS_INPUTS = {"thanks", "thank you", "thank you very much"}


def normalise(text: str) -> str:
    """Return a compact, case-insensitive representation used for matching."""
    value = text.casefold()
    for symbol, replacement in SYMBOL_ALIASES:
        value = value.replace(symbol, replacement)
    return SPACE_PATTERN.sub(" ", value.replace("_", " ")).strip()


def tokens(text: str, *, remove_stop_words: bool = True) -> tuple[str, ...]:
    found = tuple(
        TOKEN_ALIASES.get(token, token)
        for token in (item.casefold() for item in TOKEN_PATTERN.findall(normalise(text)))
    )
    if remove_stop_words:
        return tuple(token for token in found if token not in STOP_WORDS)
    return found


@dataclass(frozen=True)
class Article:
    slug: str
    title: str
    aliases: tuple[str, ...]
    summary: str
    explanation: str
    example: str
    source_url: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Article":
        required = {
            "slug",
            "title",
            "aliases",
            "summary",
            "explanation",
            "example",
            "source_url",
        }
        missing = required.difference(value)
        if missing:
            raise ValueError(f"Knowledge article is missing: {', '.join(sorted(missing))}")
        aliases = value["aliases"]
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias.strip() for alias in aliases
        ):
            raise ValueError("Every knowledge article requires a list of aliases.")
        source_url = str(value["source_url"])
        if not source_url.startswith("https://docs.python.org/3/tutorial/"):
            raise ValueError("Knowledge sources must use the official Python tutorial.")
        return cls(
            slug=str(value["slug"]).strip(),
            title=str(value["title"]).strip(),
            aliases=tuple(alias.strip() for alias in aliases),
            summary=str(value["summary"]).strip(),
            explanation=str(value["explanation"]).strip(),
            example=str(value["example"]).strip(),
            source_url=source_url,
        )


@dataclass(frozen=True)
class Response:
    answer: str
    example: str = ""
    source_url: str = ""
    related_topics: tuple[str, ...] = ()
    matched: bool = True
    topic_slug: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Response":
        return cls(
            answer=str(value.get("answer", "")),
            example=str(value.get("example", "")),
            source_url=str(value.get("source_url", "")),
            related_topics=tuple(value.get("related_topics", ())),
            matched=bool(value.get("matched", True)),
            topic_slug=str(value.get("topic_slug", "")),
        )


def load_articles(path: str | Path) -> tuple[Article, ...]:
    """Load and validate the bundled tutorial knowledge base."""
    data_path = Path(path)
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid knowledge-base JSON: {error}") from error
    if not isinstance(payload, list) or not payload:
        raise ValueError("The knowledge base must contain at least one article.")

    articles = tuple(Article.from_dict(item) for item in payload)
    slugs = [article.slug for article in articles]
    if any(not slug for slug in slugs) or len(slugs) != len(set(slugs)):
        raise ValueError("Knowledge article slugs must be present and unique.")
    return articles


class Chatbot:
    """Rank compact tutorial articles using lexical and typo-tolerant signals."""

    def __init__(self, articles: tuple[Article, ...]) -> None:
        if not articles:
            raise ValueError("At least one tutorial article is required.")
        self.articles = articles
        self._search_terms: dict[str, Counter[str]] = {}
        document_frequency: Counter[str] = Counter()

        for article in articles:
            searchable = " ".join(
                (article.title, *article.aliases, article.summary, article.explanation)
            )
            term_counts = Counter(tokens(searchable))
            self._search_terms[article.slug] = term_counts
            document_frequency.update(term_counts.keys())

        article_count = len(articles)
        self._idf = {
            term: math.log((article_count + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }

    def _score(self, article: Article, question: str) -> float:
        query_normalised = normalise(question)
        article_names = (article.title, *article.aliases)
        normalised_names = tuple(normalise(name) for name in article_names)

        if query_normalised in normalised_names:
            return 30.0

        score = 0.0
        for name in normalised_names:
            if len(name) > 2 and re.search(rf"\b{re.escape(name)}\b", query_normalised):
                score = max(score, 14.0)

        if 4 <= len(query_normalised) <= 60:
            phrase_similarity = max(
                (
                    SequenceMatcher(None, query_normalised, name).ratio()
                    for name in normalised_names
                ),
                default=0.0,
            )
            if phrase_similarity >= 0.72:
                score += phrase_similarity * 5.0

        query_terms = set(tokens(question))
        if not query_terms:
            return score

        primary_title_terms = set(tokens(article.title))
        title_terms = set(tokens(" ".join(article_names)))
        title_overlap = query_terms.intersection(title_terms)
        primary_overlap = query_terms.intersection(primary_title_terms)
        score += 7.0 * len(title_overlap) / max(1, len(query_terms))
        score += 6.0 * len(primary_overlap) / max(1, len(primary_title_terms))

        body_terms = self._search_terms[article.slug]
        score += sum(self._idf.get(term, 1.0) for term in query_terms if term in body_terms)

        for query_term in query_terms:
            if len(query_term) < 5 or query_term in body_terms:
                continue
            similarity = max(
                (
                    SequenceMatcher(None, query_term, title_term).ratio()
                    for title_term in title_terms
                    if abs(len(query_term) - len(title_term)) <= 2
                ),
                default=0.0,
            )
            if similarity >= 0.82:
                score += similarity * 4.0

            primary_similarity = max(
                (
                    SequenceMatcher(None, query_term, title_term).ratio()
                    for title_term in primary_title_terms
                    if abs(len(query_term) - len(title_term)) <= 2
                ),
                default=0.0,
            )
            if primary_similarity >= 0.82:
                score += primary_similarity * 4.0 / max(1, len(primary_title_terms))

        return score

    def search(self, question: str, limit: int = 3) -> list[tuple[Article, float]]:
        clean_question = " ".join(question.split())[:300]
        ranked = sorted(
            (
                (article, self._score(article, clean_question))
                for article in self.articles
            ),
            key=lambda item: (-item[1], item[0].title),
        )
        return ranked[: max(1, limit)]

    def answer(self, question: str, context_slug: str = "") -> Response:
        clean_question = " ".join(question.split())[:300]
        normalised_question = normalise(clean_question)

        if normalised_question in GREETING_INPUTS:
            return Response(
                "Hello. Ask me a question about a concept covered in the Python tutorial.",
                matched=False,
            )
        if normalised_question in THANKS_INPUTS:
            return Response("You are welcome. Ask another Python question whenever you are ready.", matched=False)
        if normalised_question in {"help", "topics", "what can you do"}:
            return Response(
                "I can explain Python fundamentals, collections, control flow, functions, "
                "exceptions, classes, modules, file handling, and virtual environments.",
                matched=False,
            )

        follow_up_markers = {
            "another example",
            "explain more",
            "more details",
            "show an example",
            "show me an example",
            "what about it",
            "what is that",
        }
        if context_slug and normalised_question in follow_up_markers:
            contextual_article = next(
                (article for article in self.articles if article.slug == context_slug), None
            )
            if contextual_article:
                return self._article_response(contextual_article, ())

        matches = self.search(clean_question, limit=4)
        if not matches or matches[0][1] < 3.0:
            return Response(
                "I could not find a reliable answer in the bundled Python tutorial topics. "
                "Try asking about a specific concept such as lists, loops, functions, "
                "exceptions, classes, modules, or virtual environments.",
                matched=False,
            )

        article = matches[0][0]
        related = tuple(
            candidate.title
            for candidate, score in matches[1:]
            if score >= 2.0 and candidate.slug != article.slug
        )[:2]
        return self._article_response(article, related)

    @staticmethod
    def _article_response(article: Article, related: tuple[str, ...]) -> Response:
        return Response(
            answer=f"{article.summary}\n\n{article.explanation}",
            example=article.example,
            source_url=article.source_url,
            related_topics=related,
            topic_slug=article.slug,
        )
