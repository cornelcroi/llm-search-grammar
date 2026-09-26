"""The grammar must not lie: grammar, prompt, schema and code agree."""
import json
import unittest

from examples.movies.assistant import Session, answer_schema, instructions
from examples.movies.fields import SEARCH
from examples.movies.offers import load
from examples.movies.resolve import Catalog
from search_grammar.grammar import LATER, problems

CATALOG = Catalog(*load())
RESOLVER = open("examples/movies/resolve.py").read()


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


class GrammarTest(unittest.TestCase):
    def test_grammar_prompt_and_resolver_agree(self):
        # A ready field no code handles parses correctly and then vanishes: confident results for
        # half a sentence. The worst failure this layer can have, invisible from either file alone.
        self.assertEqual(problems(SEARCH, instructions(Session(CATALOG)), RESOLVER), [])

    def test_every_later_field_says_why(self):
        for name, field in SEARCH.items():
            if field.status == LATER:
                self.assertTrue(field.why, name)

    def test_schema_is_strict_everywhere(self):
        # Strict structured output needs every property required and nothing else allowed, at every level.
        for node in walk(answer_schema()):
            if node.get("type") == "object":
                self.assertIs(node.get("additionalProperties"), False)
                self.assertEqual(sorted(node["required"]), sorted(node["properties"]))

    def test_no_field_lets_the_model_report_failure(self):
        # The model parses; only code says "cannot". A confession field hides a missing field.
        names = json.dumps(answer_schema())
        for word in ("unsupported", "cannot", "unapplied", "error"):
            self.assertNotIn(f'"{word}"', names)


if __name__ == "__main__":
    unittest.main()
