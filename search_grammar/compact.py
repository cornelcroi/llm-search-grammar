# FLOW-CRITICAL: implements flows/packs.md
# Read the doc before changing behavior here; a change that alters the flow updates the doc in the same commit.
"""The compact grammar: everything that exists, small enough for a model to hold.

Three layers, each with one job:

    INDEX       one line per item, always in the prompt. "Not on the list" means "not covered".
    DICTIONARY  what repeats across items, written ONCE. Stable, so it sits in the cached prefix.
    PACK        one item's own options, folded into families. Loaded only when the model asks.

Two compressions make it small:

    families    many raw options that differ only in a few values become ONE line:
                the values become sets, the numbers become a range.
    sharing     what every item has in common (the meaning of a mode, a quality, a language code)
                is written once in the dictionary, never repeated in a pack.

Nothing in here knows a domain. A domain says how to group its options and what to name.
"""
from collections import defaultdict
from dataclasses import dataclass, field

TOKEN_CHARS = 4  # rough size of a token in English-like text; good enough to compare, never to bill


@dataclass
class Family:
    ref: str
    key: dict
    sets: dict
    low: float
    high: float
    members: list = field(default_factory=list)


def fold(items, key, sets, number):
    """Group raw options into families.

    key     fields that define a family (e.g. service, mode). One line per distinct combination.
    sets    fields whose values are listed as a set on that line (e.g. quality, audio).
    number  the field shown as a range (e.g. price).
    """
    groups = defaultdict(list)
    for item in items:
        groups[tuple(item[k] for k in key)].append(item)

    families = []
    for i, (values, members) in enumerate(groups.items(), start=1):
        found = {name: sorted({_one(m[name]) for m in members}) for name in sets}
        numbers = [m[number] for m in members]
        families.append(Family(ref=f"f{i}", key=dict(zip(key, values)), sets=found,
                               low=min(numbers), high=max(numbers), members=members))
    return families


def _one(value):
    # A list value (the subtitles of an offer) is one option, not several.
    return ",".join(value) if isinstance(value, list) else value


def tokens(text):
    return max(1, round(len(text) / TOKEN_CHARS))
