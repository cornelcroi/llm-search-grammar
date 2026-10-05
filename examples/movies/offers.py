# FLOW-CRITICAL: implements flows/packs.md
# Read the doc before changing behavior here; a change that alters the flow updates the doc in the same commit.
"""The watch offers of the movie example, as a compact grammar.

The offers are INVENTED (scripts/generate_offers.py): fictional services, made-up prices. They stand
for any catalogue where each item carries its own large set of options that no model has seen.
"""
import json
from pathlib import Path

from search_grammar.compact import fold

DATA = Path(__file__).resolve().parents[2] / "data"

FAMILY_KEY = ["service", "mode"]
FAMILY_SETS = ["edition", "quality", "audio", "sound", "subtitles"]

# Written once, for every film. Everything a pack line abbreviates is explained here.
DICTIONARY = """\
OFFERS: how a film can be watched. One family per line:
  f<n> {service} · {mode} · {editions} · {qualities} · audio {languages} · sound {formats} · subs {languages} · {price}
modes: subscription = included with the service · free = with ads · rent = 48 hours · buy = yours to keep
editions, named per film: theatrical · {director}'s cut · extended (+{m} min) · {n}th anniversary · IMAX enhanced · with commentary by {person}
qualities: SD · HD · 4K    sound: stereo · 5.1 · atmos
languages: en English · fr French · de German · es Spanish · it Italian · pt Portuguese · nl Dutch · pl Polish · ro Romanian · ja Japanese · ru Russian · sv Swedish · ar Arabic
services: StreamOne, CinePass, ClassicVault, NightOwl (subscription) · PopcornPlus (free) · RentBox, FlixMarket (rent, buy) · VidaStore (buy)
A family lists what exists for this film. Anything not in the pack does not exist for this film."""


def load():
    films = json.loads((DATA / "films.json").read_text())
    offers = json.loads((DATA / "offers.json").read_text())
    by_film = {}
    for offer in offers:
        by_film.setdefault(offer["film"], []).append(offer)
    return films, by_film


def index_line(ref, film, count):
    """One line per film, always in the prompt: enough to recognise it, nothing more."""
    return f"{ref} {film['title']} ({film['year']}) · {count} offers"


def pack(film, offers):
    """One film's offers, folded into families: the text the model reads, and the families code keeps."""
    families = fold(offers, FAMILY_KEY, FAMILY_SETS, "price")
    lines = [f"PACK {film['title']} ({film['year']}) · {len(offers)} offers in {len(families)} families"]
    for f in families:
        subs = sorted({s for combo in f.sets["subtitles"] for s in combo.split(",")})
        price = "included" if f.high == 0 else f"{f.low:.2f}–{f.high:.2f} €" if f.low != f.high else f"{f.low:.2f} €"
        lines.append(" · ".join([
            f"{f.ref} {f.key['service']}", f.key["mode"], "/".join(f.sets["edition"]), "/".join(f.sets["quality"]),
            "audio " + ",".join(f.sets["audio"]), "sound " + ",".join(f.sets["sound"]), "subs " + ",".join(subs), price,
        ]))
    return "\n".join(lines), families


def raw_line(offer):
    """How a naive prompt would carry one offer: every option on its own line."""
    return (f"{offer['id']} {offer['service']} {offer['mode']} {offer['edition']} {offer['quality']} "
            f"audio={offer['audio']} sound={offer['sound']} subs={','.join(offer['subtitles'])} {offer['price']:.2f}")
