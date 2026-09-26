"""The forgiving search: loose words find the real thing, and say how sure they are."""
import unittest

from examples.movies.offers import load
from examples.movies.resolve import Catalog
from search_grammar.forgiving import find, similarity, spot

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

    def spotted(self, sentence):
        return [(CATALOG.by_id[m.key]["title"], CATALOG.by_id[m.key]["year"]) for m in spot(sentence, CATALOG.titles)]

    def test_a_title_in_another_script_never_matches_everything(self):
        # Parasite's and Seven Samurai's original titles normalise to nothing; they once matched every sentence.
        self.assertEqual(self.spotted("a 90s Tom Hanks comedy I can rent tonight"), [])

    def test_a_misspelt_long_title_is_spotted(self):
        self.assertEqual(self.spotted("inceptoin with nolan talking over it"), [("Inception", 2010)])

    def test_an_exact_title_wins_over_a_loose_one_on_the_same_words(self):
        self.assertEqual(self.spotted("le parrain en version longue"), [("The Godfather", 1972)])

    def test_a_short_title_must_be_exact(self):
        self.assertEqual(self.spotted("a film with a car chase"), [])
        self.assertIn(("Cars", 2006), self.spotted("the cars kind"))

    def test_nothing_under_the_floor(self):
        self.assertEqual(find("zzzz qqqq", CATALOG.people), [])


if __name__ == "__main__":
    unittest.main()
