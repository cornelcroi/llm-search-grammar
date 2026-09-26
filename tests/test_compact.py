"""The compact grammar: smaller, and still exact about what exists."""
import unittest

from examples.movies.offers import DICTIONARY, load, pack, raw_line
from search_grammar.compact import tokens

FILMS, OFFERS = load()


class CompactTest(unittest.TestCase):
    def test_every_offer_lives_in_exactly_one_family(self):
        for film in FILMS:
            offers = OFFERS.get(film["id"], [])
            _, families = pack(film, offers)
            members = [o["id"] for f in families for o in f.members]
            self.assertEqual(sorted(members), sorted(o["id"] for o in offers), film["title"])

    def test_a_family_line_covers_its_members(self):
        for film in FILMS[:50]:
            _, families = pack(film, OFFERS.get(film["id"], []))
            for f in families:
                for o in f.members:
                    self.assertIn(o["edition"], f.sets["edition"])
                    self.assertIn(o["quality"], f.sets["quality"])
                    self.assertTrue(f.low <= o["price"] <= f.high)

    def test_a_pack_is_much_smaller_than_its_offers(self):
        film = next(f for f in FILMS if len(OFFERS.get(f["id"], [])) > 100)
        text, _ = pack(film, OFFERS[film["id"]])
        raw = "\n".join(raw_line(o) for o in OFFERS[film["id"]])
        self.assertLess(tokens(text) * 5, tokens(raw))

    def test_the_dictionary_says_what_absence_means(self):
        self.assertIn("Anything not in the pack does not exist for this film", DICTIONARY)


if __name__ == "__main__":
    unittest.main()
