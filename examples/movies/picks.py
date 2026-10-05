# FLOW-CRITICAL: implements flows/packs.md
# Read the doc before changing behavior here; a change that alters the flow updates the doc in the same commit.
"""The model points; code owns the ids.

A pick names a film ref, a family ref and some values. Code checks each against the pack it was
read from, then returns the REAL offer: its id and its price never passed through the model.

    strict   an offer has every value asked for
    partial  none does: the closest real offer, and which wish does not exist for this film
    dropped  the pick points at nothing loaded: a bad pointer is dropped and said, never guessed
"""
from search_grammar.forgiving import CLOSE, similarity

from examples.movies.resolve import CODES

CHOICES = ("edition", "quality", "audio", "sound")


def _fits(offer, choice, value):
    if choice == "edition":
        return similarity(value, offer["edition"]) >= CLOSE
    if choice == "audio":
        return offer["audio"] == CODES.get(value.lower(), value.lower())
    return offer[choice].lower() == value.lower()


def check(pick, session, named):
    """`named` holds the ids of the films the sentence named: a pick at any other film is the model
    choosing on the viewer's behalf, and is dropped whatever the prompt said."""
    film_id = session.refs.get(pick["film"])
    if film_id not in session.loaded:
        return {"verdict": "dropped", "why": f"{pick['film']} was not loaded"}
    if film_id not in named:
        film = session.catalog.by_id[film_id]
        return {"verdict": "dropped", "why": f"{film['title']} ({film['year']}) was not named in the sentence"}
    _, families = session.loaded[film_id]
    family = next((f for f in families if f.ref == pick["family"]), None)
    if not family:
        return {"verdict": "dropped", "why": f"{pick['family']} is not a family of {pick['film']}"}

    wanted = {c: pick[c] for c in CHOICES if pick.get(c)}
    film = session.catalog.by_id[film_id]
    scored = [(sum(_fits(o, c, v) for c, v in wanted.items()), o) for o in family.members]
    best_score = max(s for s, _ in scored)
    best = min((o for s, o in scored if s == best_score), key=lambda o: o["price"])
    missing = []
    for choice, value in wanted.items():
        if _fits(best, choice, value):
            continue
        # Not in this family is not the same as not for this film: say where it does exist.
        elsewhere = sorted({f"{f.key['service']} {f.key['mode']}" for f in families
                            if any(_fits(o, choice, value) for o in f.members)})
        missing.append(f"{choice} {value} (not with {family.key['service']} {family.key['mode']}; "
                       + (f"only on {', '.join(elsewhere)})" if elsewhere else "nowhere for this film)"))
    return {
        "verdict": "strict" if not missing else "partial",
        "film": f"{film['title']} ({film['year']})",
        "offer": best["id"],
        "what": f"{best['service']} · {best['mode']} · {best['edition']} · {best['quality']} · "
                f"audio {best['audio']} · {best['sound']}",
        "price": best["price"],
        "missing": missing,
    }
