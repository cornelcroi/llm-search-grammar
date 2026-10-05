"""Run a sentence through the grammar and show every step.

    python3 -m examples.movies "inceptoin with nolan talking over it"

Needs OPENAI_API_KEY. Films are real (Wikidata); the ways to watch them are invented.
The same steps, in a browser: python3 -m examples.movies.web
"""
import json
import sys

from examples.movies.assistant import Session
from examples.movies.explain import explain
from examples.movies.offers import load
from examples.movies.resolve import Catalog


def price(value):
    return "included" if value == 0 else f"{value:.2f} €"


def main():
    sentence = " ".join(sys.argv[1:]) or "inceptoin with nolan talking over it"
    films, offers = load()
    session = Session(Catalog(films, offers))

    print(f'\n"{sentence}"\n')
    steps = explain(sentence, session)

    print(f"1 · CODE loads the lines of the films the sentence names, then ONE call to {steps['model']}")
    for step in steps["trace"]:
        print(f"    code    {step}")
    for query in steps["queries"]:
        print(f"    parsed  {json.dumps(query['parsed'], ensure_ascii=False)}")
    for pick in steps["picks"]:
        print(f"    points  {json.dumps(pick['pointer'], ensure_ascii=False)}")

    print("\n2 · CODE, decides what can be applied")
    for query in steps["queries"]:
        for key, value in query["report"].items():
            print(f"    {key:<13}{json.dumps(value, ensure_ascii=False)}")
        total = query["total"]
        print(f"\n3 · RESULTS, {total} film{'s' if total != 1 else ''}" + (f" for '{query['label']}'" if query["label"] else ""))
        for film in query["films"]:
            line = f"    {film['title']} ({film['year']})"
            if "way" in film:
                w = film["way"]
                line += f"  ·  {w['service']} {w['mode']} {w['quality']} audio {w['audio']} · {w['edition']} · {price(w['price'])}"
            print(line)

    if steps["picks"]:
        print("\n4 · POINTERS, checked against the pack by code")
        for pick in steps["picks"]:
            result = pick["result"]
            if result["verdict"] == "dropped":
                print(f"    dropped  {result['why']}")
                continue
            print(f"    {result['verdict']:<8} {result['film']} · {result['what']} · {price(result['price'])}  [{result['offer']}]")
            for gap in result["missing"]:
                print(f"             missing  {gap}")

    u = steps["usage"]
    print(f"\n{u['calls']} model call{'s' if u['calls'] > 1 else ''} · {u['prompt_tokens']:,} prompt tokens "
          f"({u['cached_tokens']:,} cached) · {u['completion_tokens']:,} completion tokens\n")


if __name__ == "__main__":
    main()
