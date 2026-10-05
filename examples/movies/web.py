# FLOW-CRITICAL: implements flows/search.md
# Read the doc before changing behavior here; a change that alters the flow updates the doc in the same commit.
"""The same search, in a browser: posters, and every step code took.

    python3 -m examples.movies.web          ->  http://127.0.0.1:8000
    python3 -m examples.movies.web 8080     ->  another port

Standard library only. Needs OPENAI_API_KEY (or .env), like the terminal demo. Listens on localhost only.
Posters load from TMDB's image server: no TMDB key needed to run it.
"""
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from examples.movies.assistant import Session
from examples.movies.explain import explain
from examples.movies.offers import load
from examples.movies.resolve import Catalog

PAGE = Path(__file__).resolve().parent / "web.html"
FILMS, OFFERS = load()
CATALOG = Catalog(FILMS, OFFERS)


def answer(sentence):
    """JSON for one search. A missing key or a failed model call comes back as a message, not a crash."""
    if not sentence.strip():
        return 400, {"error": "Type a sentence."}
    try:
        return 200, explain(sentence, Session(CATALOG))
    except SystemExit as e:  # llm.py exits with a message the user can act on (no key, call failed)
        return 502, {"error": str(e)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/":
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/search":
            sentence = urllib.parse.parse_qs(url.query).get("q", [""])[0]
            status, body = answer(sentence)
            self._send(status, json.dumps(body, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def _send(self, status, body, kind):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        sys.exit(f"Port {port} is busy. Pick another one: python3 -m examples.movies.web 8080")
    print(f"Search grammar demo on http://127.0.0.1:{port}  ({len(FILMS)} films). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
