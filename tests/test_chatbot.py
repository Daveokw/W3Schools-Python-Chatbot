from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from chatbot import Chatbot, Response, load_articles

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"


class ChatbotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.articles = load_articles(DATA_PATH)
        cls.chatbot = Chatbot(cls.articles)

    def test_knowledge_base_is_complete_and_unique(self) -> None:
        self.assertGreaterEqual(len(self.articles), 40)
        self.assertEqual(
            len({article.slug for article in self.articles}), len(self.articles)
        )
        for article in self.articles:
            self.assertTrue(article.summary)
            self.assertTrue(article.example)
            self.assertTrue(
                article.source_url.startswith("https://docs.python.org/3/tutorial/")
            )

    def test_every_topic_title_and_primary_alias_retrieve_the_same_topic(self) -> None:
        for expected in self.articles:
            for phrase in (expected.title, expected.aliases[0]):
                with self.subTest(topic=expected.title, phrase=phrase):
                    actual, _ = self.chatbot.search(f"Explain {phrase}", limit=1)[0]
                    self.assertEqual(actual.slug, expected.slug)

    def test_displayed_python_examples_have_valid_syntax(self) -> None:
        for article in self.articles:
            if article.slug == "virtual-environments":
                continue
            with self.subTest(topic=article.title):
                ast.parse(article.example)

    def test_common_questions_select_the_expected_topics(self) -> None:
        cases = {
            "What is a Python list?": "Lists",
            "How do functions work?": "Functions",
            "Explain list comprehensions": "List comprehensions",
            "What is the difference between a list and a tuple?": "Lists compared with tuples",
            "How can I handle an exception?": "Exceptions",
            "How do I create a virtual environment?": "Virtual environments and packages",
        }
        for question, expected_title in cases.items():
            with self.subTest(question=question):
                top_article, _ = self.chatbot.search(question, limit=1)[0]
                self.assertEqual(top_article.title, expected_title)

    def test_minor_typo_can_still_match_a_topic(self) -> None:
        response = self.chatbot.answer("What are functons?")
        self.assertTrue(response.matched)
        self.assertIn("reusable block of code", response.answer)

    def test_symbols_and_common_synonyms_are_understood(self) -> None:
        cases = {
            "What does [] mean?": "Lists",
            "How does == work?": "Comparisons and Boolean logic",
            "Explain arrays": "Lists",
            "What is a hashmap?": "Dictionaries",
        }
        for question, expected_title in cases.items():
            with self.subTest(question=question):
                article, _ = self.chatbot.search(question, limit=1)[0]
                self.assertEqual(article.title, expected_title)

    def test_short_follow_up_uses_the_previous_topic(self) -> None:
        first = self.chatbot.answer("What is a generator?")
        follow_up = self.chatbot.answer("explain more", context_slug=first.topic_slug)
        self.assertTrue(follow_up.matched)
        self.assertEqual(follow_up.topic_slug, "iterators-generators")

    def test_out_of_scope_question_is_not_forced_to_an_article(self) -> None:
        response = self.chatbot.answer("How do I cook rice?")
        self.assertFalse(response.matched)
        self.assertFalse(response.source_url)
        self.assertIn("could not find a reliable answer", response.answer)

    def test_conversational_inputs_receive_short_responses(self) -> None:
        for message in ("hello", "thank you", "help"):
            with self.subTest(message=message):
                response = self.chatbot.answer(message)
                self.assertFalse(response.matched)
                self.assertFalse(response.source_url)

    def test_response_round_trip_preserves_display_data(self) -> None:
        original = self.chatbot.answer("Explain dictionaries")
        restored = Response.from_dict(original.to_dict())
        self.assertEqual(restored, original)

    def test_loader_rejects_unofficial_source_urls(self) -> None:
        invalid_article = {
            "slug": "invalid",
            "title": "Invalid",
            "aliases": ["invalid"],
            "summary": "Invalid source.",
            "explanation": "Invalid source.",
            "example": "pass",
            "source_url": "https://example.com/tutorial",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.json"
            path.write_text(json.dumps([invalid_article]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "official Python tutorial"):
                load_articles(path)


if __name__ == "__main__":
    unittest.main()
