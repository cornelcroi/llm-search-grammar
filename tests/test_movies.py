"""Real model answers (tests/answers.json), replayed through code. No API key needed.

What is tested is code's side: given what the model said, does code apply, refuse, point and
explain correctly. Record new answers with scripts/record_answers.py.
"""
import json
import unittest
from pathlib import Path

from examples.movies.assistant import Session
from examples.movies.offers import load
from examples.movies.picks import check
from examples.movies.resolve import Catalog, resolve, search, why_nothing

CATALOG = Catalog(*load())
RECORDS = {r["sentence"]: r for r in json.loads((Path(__file__).parent / "answers.json").read_text())}
OFFERS = {o["id"]: o for offers in CATALOG.offers.values() for o in offers}


def replay(sentence):
    record = RECORDS[sentence]
    session = Session(CATALOG)
    for names in record["loads"]:
        session.load(names)
    answer = record["answer"]
    results = []
    for query in answer["queries"]:
        filters, watch, report = resolve(query, CATALOG)
        found, total, relaxed = search(filters, watch, CATALOG)
        report["why_nothing"] = why_nothing(filters, watch, CATALOG) if not total else None
        results.append((found, total, report))
    named = {CATALOG.film(f["title"], f["year"])[0].key for q in answer["queries"] for f in q["films"]}
    picks = [check(p, session, named) for p in answer["picks"]]
    return results, picks


class MoviesTest(unittest.TestCase):
    def test_the_long_version_points_into_the_pack_and_code_owns_the_price(self):
        _, picks = replay("the long version of Titanic in French, the cheapest way")
        pick = next(p for p in picks if p.get("offer") and OFFERS[p["offer"]]["edition"] == "extended (+37 min)")
        self.assertEqual(pick["verdict"], "partial")
        offer = OFFERS[pick["offer"]]
        # The id and the price come from the data, never from the model's text.
        self.assertEqual((offer["edition"], offer["price"]), ("extended (+37 min)", pick["price"]))
        self.assertIn("only on CinePass subscription", pick["missing"][0])

    def test_an_empty_answer_says_why(self):
        results, _ = replay("a 90s Tom Hanks comedy I can rent tonight in French for under 4 euros")
        found, total, report = results[0]
        self.assertEqual(total, 0)
        self.assertIn("audio", report["why_nothing"])

    def test_understood_but_not_possible_is_reported_with_the_reason(self):
        results, _ = replay("a cosy film like Forrest Gump for my 6 year old, without Tom Cruise")
        found, _, report = results[0]
        self.assertEqual(report["cannot"]["similar_to"]["why"], "needs a similarity layer")
        self.assertEqual(report["cannot"]["mood"]["why"], "no mood data in this catalogue")
        for film, _ in found:
            # The dictionary field: code decided what "6 years old" means here, not the model.
            self.assertTrue({"Family", "Animation"} & set(film["genres"]), film["title"])
            self.assertNotIn("Tom Cruise", film["cast"])

    def test_two_wishes_with_different_shapes_stay_two_requests(self):
        results, _ = replay("a comedy with De Niro or a drama with Kevin Costner")
        self.assertEqual(len(results), 2)
        for (found, _, report), genre in zip(results, ("Comedy", "Drama")):
            self.assertEqual(report["applied"]["genre"], [genre])

    def test_a_reference_says_the_people_it_used_and_the_ambiguity(self):
        results, _ = replay("something with the actors from Titanic, in 4K")
        _, _, report = results[0]
        self.assertIn("Kate Winslet", report["applied"]["cast"])
        self.assertEqual(report["applied"]["through"], ["Titanic (1997)"])
        self.assertTrue(any("1953" in d for d in report["did_you_mean"]))

    def test_a_wish_the_pack_does_not_list_does_not_exist(self):
        _, picks = replay("inceptoin with nolan talking over it")
        self.assertEqual(picks[0]["verdict"], "partial")
        self.assertIn("nowhere for this film", picks[0]["missing"][0])

    def test_a_pointer_at_an_unnamed_film_is_dropped_by_code(self):
        session = Session(CATALOG)
        session.load(["Forrest Gump"])
        ref = next(r for r, fid in session.refs.items() if CATALOG.by_id[fid]["title"] == "Forrest Gump")
        pick = {"film": ref, "family": "f1", "edition": None, "quality": None, "audio": None, "sound": None}
        self.assertEqual(check(pick, session, named=set())["verdict"], "dropped")


if __name__ == "__main__":
    unittest.main()


class OneCallTest(unittest.TestCase):
    def test_a_word_that_is_also_a_title_is_not_taken_for_the_film(self):
        results, picks = replay("something taken seriously, a drama, not the cars kind")
        self.assertEqual(RECORDS["something taken seriously, a drama, not the cars kind"]["answer"]["queries"][0]["films"], [])
        self.assertEqual(picks, [])
