"""Record real model answers for the tests, so they run without an API key.

    OPENAI_API_KEY=... python3 scripts/record_answers.py

Each record keeps the sentence, the packs the model asked for, and its answer, exactly as returned.
Rerun after changing the grammar or the prompt, and read the diff: it shows what the model now does.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from examples.movies.assistant import Session, ask  # noqa: E402
from examples.movies.offers import load  # noqa: E402
from examples.movies.resolve import Catalog  # noqa: E402
from search_grammar.llm import model  # noqa: E402

SENTENCES = [
    "the long version of Titanic in French, the cheapest way",
    "a 90s Tom Hanks comedy I can rent tonight in French for under 4 euros",
    "a cosy film like Forrest Gump for my 6 year old, without Tom Cruise",
    "a comedy with De Niro or a drama with Kevin Costner",
    "something with the actors from Titanic, in 4K",
    "inceptoin with nolan talking over it",
]
OUT = Path(__file__).resolve().parent.parent / "tests" / "answers.json"


def main():
    catalog = Catalog(*load())
    records = []
    for sentence in SENTENCES:
        session = Session(catalog)
        loads = []
        original = session.load
        session.load = lambda names, _o=original: (loads.append(names), _o(names))[1]
        answer, _ = ask(sentence, session)
        records.append({"sentence": sentence, "model": model(), "loads": loads, "answer": answer})
        print(f"recorded: {sentence}")
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
