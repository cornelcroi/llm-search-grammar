"""The forgiving search: loose words find the real thing, and say how sure they are."""
import unittest

from examples.movies.offers import load
from examples.movies.resolve import Catalog
from search_grammar.forgiving import find, similarity

CATALOG = Catalog(*load())


class ForgivingTest(unittest.TestCase):
    def film(self, title, year=None):
        match, others = CATALOG.film(title, year)
        return CATALOG.by_id[match.key], match.band, [CATALOG.by_id[o.key]["year"] for o in others]

    def test_a_typo_is_close_not_exact(self):
        film, band, _ = self.film("inceptoin")
        self.assertEqual((film["title"], band), ("Inception", "close"))

    def test_any_language_finds_the_film(self):
        film, band, _ = self.film("le parrain")
        self.assertEqual((film["title"], band), ("The Godfather", "exact"))

    def test_an_ambiguous_title_is_reported_never_hidden(self):
        film, _, others = self.film("titanic")
        self.assertEqual(film["year"], 1997)  # the most known of the three
        self.assertEqual(sorted(others), [1943, 1953])

    def test_a_year_settles_the_ambiguity(self):
        film, _, others = self.film("Titanic", 1953)
        self.assertEqual((film["year"], others), (1953, []))

    def test_a_surname_finds_the_person_but_never_exactly(self):
        best = find("nolan", CATALOG.people, limit=1)[0]
        self.assertEqual((best.name, best.band), ("Christopher Nolan", "close"))

    def test_meaning_is_not_spelling(self):
        # Why the model reads the pack: no fuzzy match turns "the long version" into the edition.
        self.assertLess(similarity("the long version", "extended (+37 min)"), 0.6)
        self.assertGreater(similarity("cameron cut", "Cameron's cut"), 0.8)

    def test_nothing_under_the_floor(self):
        self.assertEqual(find("zzzz qqqq", CATALOG.people), [])


if __name__ == "__main__":
    unittest.main()
