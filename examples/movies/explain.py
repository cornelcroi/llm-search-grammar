"""One search, every step, as data: what code loaded, what the model parsed, what code applied and why,
the films found, the pointers checked. The terminal demo prints it, the web demo shows it.
"""
from examples.movies.assistant import ask
from examples.movies.picks import check
from examples.movies.resolve import resolve, search, why_nothing
from search_grammar.llm import model

POSTER = "https://image.tmdb.org/t/p/w342{}"
REPORT_KEYS = ("applied", "cannot", "unapplied", "did_you_mean", "relaxed", "why_nothing")


def filled(query):
    """Only what the model actually set, so the step reads like the sentence."""
    return {k: v for k, v in query.items() if v not in (None, [], "", False) and
            not (k in ("genre_mode", "cast_mode") and v == "any")}


def _film(film, ways):
    out = {"id": film["id"], "title": film["title"], "year": film["year"], "genres": film["genres"],
           "directors": film["directors"], "poster": POSTER.format(film["poster"]) if film.get("poster") else None}
    if ways:
        o = ways[0]
        out["way"] = {k: o[k] for k in ("service", "mode", "quality", "audio", "edition", "price")}
    return out


def explain(sentence, session, answer=None, usage=None):
    """Run the sentence through the grammar. `answer` replays a recorded model answer (the tests);
    without it, the model is called once."""
    if answer is None:
        answer, usage = ask(sentence, session)
    usage = usage or []
    steps = {"sentence": sentence, "model": model(), "trace": list(session.trace), "queries": [], "picks": []}

    for query in answer["queries"]:
        filters, watch, report = resolve(query, session.catalog)
        found, total, relaxed = search(filters, watch, session.catalog)
        report["relaxed"] = relaxed
        if not total:
            report["why_nothing"] = why_nothing(filters, watch, session.catalog)
        steps["queries"].append({
            "parsed": filled(query),
            "report": {k: report[k] for k in REPORT_KEYS if report.get(k)},
            "label": report.get("label"),
            "total": total,
            "films": [_film(film, ways) for film, ways in found],
        })

    named = set()
    for query in answer["queries"]:
        for wanted in query["films"]:
            match, _ = session.catalog.film(wanted["title"], wanted["year"])
            if match:
                named.add(match.key)
    for pick in answer["picks"]:
        steps["picks"].append({"pointer": {k: v for k, v in pick.items() if v}, "result": check(pick, session, named)})

    steps["usage"] = {
        "calls": len(usage),
        "prompt_tokens": sum(u.get("prompt_tokens", 0) for u in usage),
        "cached_tokens": sum(u.get("prompt_tokens_details", {}).get("cached_tokens", 0) for u in usage),
        "completion_tokens": sum(u.get("completion_tokens", 0) for u in usage),
    }
    return steps
