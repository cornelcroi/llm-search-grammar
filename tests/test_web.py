"""The web demo, without an API key: real model answers (tests/answers.json) replayed through the server.

What is tested: the page is served with its TMDB attribution, /search returns the films with their
posters and every step, a model failure comes back as a message, and every film has a poster to show.
"""
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import examples.movies.web as web
from examples.movies.assistant import Session
from examples.movies.explain import POSTER, explain

RECORDS = {r["sentence"]: r for r in json.loads((Path(__file__).parent / "answers.json").read_text())}


def replayed(sentence, session):
    """explain() with the recorded answer instead of a model call."""
    record = RECORDS[sentence]
    for names in record["loads"]:
        session.load(names)
    return explain(sentence, session, answer=record["answer"], usage=[])


class WebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.real_explain = web.explain

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        web.explain = cls.real_explain

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as r:
                return r.status, r.headers.get("Content-Type"), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read()

    def test_the_page_is_served_with_the_tmdb_attribution(self):
        status, kind, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", kind)
        self.assertIn(b"This product uses the TMDB API but is not endorsed or certified by TMDB", body)

    def test_search_returns_films_with_posters_and_every_step(self):
        web.explain = lambda sentence, session: replayed(sentence, session)
        sentence = "something with the actors from Titanic, in 4K"
        status, kind, body = self.get("/search?q=" + urllib.parse.quote(sentence))
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("application/json", kind)
        films = data["queries"][0]["films"]
        self.assertTrue(films)
        for film in films:
            self.assertTrue(film["poster"].startswith("https://image.tmdb.org/t/p/"))
            self.assertIn("way", film)  # "in 4K" asks for a way to watch: each film shows the offer it matched
            self.assertEqual(film["way"]["quality"], "4K")
        self.assertIn("applied", data["queries"][0]["report"])
        self.assertIn("parsed", data["queries"][0])

    def test_a_model_failure_comes_back_as_a_message_not_a_crash(self):
        def no_key(sentence, session):
            raise SystemExit("OPENAI_API_KEY is not set.")
        web.explain = no_key
        status, _, body = self.get("/search?q=anything")
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body)["error"], "OPENAI_API_KEY is not set.")

    def test_an_empty_sentence_is_refused(self):
        status, _, body = self.get("/search?q=")
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))


class PosterDataTest(unittest.TestCase):
    def test_every_film_has_a_poster_path(self):
        for film in web.FILMS:
            self.assertRegex(film.get("poster") or "", r"^/\w+\.jpg$", film["title"])

    def test_poster_urls_are_built_from_the_path(self):
        session = Session(web.CATALOG)
        data = replayed("a cosy film like Forrest Gump for my 6 year old, without Tom Cruise", session)
        for film in data["queries"][0]["films"]:
            path = web.CATALOG.by_id[film["id"]]["poster"]
            self.assertEqual(film["poster"], POSTER.format(path))


if __name__ == "__main__":
    unittest.main()
