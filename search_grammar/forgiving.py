"""The forgiving search: loose words in, the real thing out, and an honest word about how sure.

A compact grammar lets the model write loose words ("inceptoin", "the nolan one", "cameron cut").
It only works because code forgives them: accents and case ignored, typos tolerated, a surname
found inside a full name. Neither works alone.

Confidence comes back as a word, never a number: a float on screen claims a precision it does not
have. `exact` is applied, `close` is applied and said, `unsure` is offered as a question.
"""
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

EXACT = 0.95
CLOSE = 0.80
FLOOR = 0.60  # below this, no match at all


@dataclass(frozen=True)
class Match:
    key: str
    name: str
    score: float

    @property
    def band(self):
        return "exact" if self.score >= EXACT else "close" if self.score >= CLOSE else "unsure"


def normalize(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9+]+", " ", text).strip()


def similarity(wanted, name):
    """How well `wanted` names `name`: the whole name, or a run of its words ("nolan", "godfather")."""
    a, b = normalize(wanted), normalize(name)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    best = SequenceMatcher(None, a, b).ratio()
    words, size = b.split(), len(a.split())
    for i in range(len(words) - size + 1):
        part = " ".join(words[i:i + size])
        # A part of the name is a weaker claim than the whole name, so it never reaches `exact`.
        best = max(best, SequenceMatcher(None, a, part).ratio() * 0.94)
    return best


def find(wanted, candidates, limit=3):
    """Best matches for `wanted` among {key: [names]}, strongest first, nothing under FLOOR.

    Several candidates at the same score is an ambiguity the caller must report, never resolve
    silently: three films are called Titanic.
    """
    scored = []
    for key, names in candidates.items():
        score = max((similarity(wanted, n) for n in names if n), default=0.0)
        if score >= FLOOR:
            scored.append(Match(key, names[0], round(score, 3)))
    return sorted(scored, key=lambda m: -m.score)[:limit]
