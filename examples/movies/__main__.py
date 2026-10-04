"""Run a sentence through the grammar and show every step.

    python3 -m examples.movies "inceptoin with nolan talking over it"

Needs OPENAI_API_KEY. Films are real (Wikidata); the ways to watch them are invented.
"""
import json
import sys

from examples.movies.assistant import Session, ask
from examples.movies.offers import load
from examples.movies.picks import check
from examples.movies.resolve import Catalog, resolve, search, why_nothing
from search_grammar.llm import model


def filled(query):
    """Only what the model actually set, so the step reads like the sentence."""
    return {k: v for k, v in query.items() if v not in (None, [], "", False) and
            not (k in ("genre_mode", "cast_mode") and v == "any")}


def main():
    sentence = " ".join(sys.argv[1:]) or "inceptoin with nolan talking over it"
    films, offers = load()
    session = Session(Catalog(films, offers))

    print(f'\n"{sentence}"\n')
    answer, usage = ask(sentence, session)

    print(f"1 · CODE loads the lines of the films the sentence names, then ONE call to {model()}")
    for step in session.trace:
        print(f"    code    {step}")
    for query in answer["queries"]:
        print(f"    parsed  {json.dumps(filled(query), ensure_ascii=False)}")
    for pick in answer["picks"]:
        print(f"    points  {json.dumps({k: v for k, v in pick.items() if v}, ensure_ascii=False)}")

    print("\n2 · CODE, decides what can be applied")
    for query in answer["queries"]:
        filters, watch, report = resolve(query, session.catalog)
        found, total, relaxed = search(filters, watch, session.catalog)
        report["relaxed"] = relaxed
        if not total:
            report["why_nothing"] = why_nothing(filters, watch, session.catalog)
        for key in ("applied", "cannot", "unapplied", "did_you_mean", "relaxed", "why_nothing"):
            if report.get(key):
                print(f"    {key:<13}{json.dumps(report[key], ensure_ascii=False)}")
        print(f"\n3 · RESULTS, {total} film{'s' if total != 1 else ''}" + (f" for '{report['label']}'" if report["label"] else ""))
        for film, ways in found:
            line = f"    {film['title']} ({film['year']})"
            if ways:
                o = ways[0]
                price = "included" if o["price"] == 0 else f"{o['price']:.2f} €"
                line += f"  ·  {o['service']} {o['mode']} {o['quality']} audio {o['audio']} · {o['edition']} · {price}"
            print(line)

    if answer["picks"]:
        named = set()
        for query in answer["queries"]:
            for wanted in query["films"]:
                match, _ = session.catalog.film(wanted["title"], wanted["year"])
                if match:
                    named.add(match.key)
        print("\n4 · POINTERS, checked against the pack by code")
        for pick in answer["picks"]:
            result = check(pick, session, named)
            if result["verdict"] == "dropped":
                print(f"    dropped  {result['why']}")
                continue
            price = "included" if result["price"] == 0 else f"{result['price']:.2f} €"
            print(f"    {result['verdict']:<8} {result['film']} · {result['what']} · {price}  [{result['offer']}]")
            if result["missing"]:
                for gap in result["missing"]:
                    print(f"             missing  {gap}")

    prompt = sum(u.get("prompt_tokens", 0) for u in usage)
    cached = sum(u.get("prompt_tokens_details", {}).get("cached_tokens", 0) for u in usage)
    print(f"\n{len(usage)} model call{'s' if len(usage) > 1 else ''} · {prompt:,} prompt tokens "
          f"({cached:,} cached) · {sum(u.get('completion_tokens', 0) for u in usage):,} completion tokens\n")


if __name__ == "__main__":
    main()
