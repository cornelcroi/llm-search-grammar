"""The model's side: read the sentence against the grammar, ask for packs, point.

In the prompt, always: the rules, the grammar, the index of films, the offers dictionary. On
demand: a film's pack, when the model asks for it with load_film. The model returns a structured
object and never a sentence to show; code turns it into results and says what it did.
"""
import json
import re

from search_grammar.grammar import listing, schema
from search_grammar.llm import chat

from examples.movies.fields import PICK, SEARCH
from examples.movies.offers import DICTIONARY, index_line, pack

SLOTS = 2  # packs kept in context; loading a third drops the oldest

RULES = """\
READ, DO NOT JUDGE, AND NEVER REPORT FAILURE
  Fill every field the sentence asks for, best effort. There is no field to say something cannot be
  done and you must never try: code that knows the catalogue decides that afterwards. A wish that
  seems to fit nowhere goes in the closest field, never nowhere. An empty object is a correct answer
  for a sentence that asks for nothing.
  Name no rating code, no country's rules, no id. "for a 6 year old" is age 6.

NAMES AND TITLES
  Correct a spelling you recognise and complete a surname: "tarentino" is Quentin Tarantino. A name you
  do not recognise passes through as written. Titles pass through as typed, never translated.
  NEVER add a film or a person the sentence did not name. "a 90s Tom Hanks comedy" names no film:
  finding which films fit is the search's job, not yours. "tonight" and "now" are not an occasion.

ONE SENTENCE, ONE REQUEST, USUALLY
  "a French comedy from the 90s" is ONE request. A second appears only when wishes have different shapes
  and pairing them matters: "a comedy with De Niro or a drama with Kevin Costner" is TWO.
  label is the request in the viewer's words, four or five of them.

SIMILARITY IS NOT A FILM, A TOPIC IS NOT A GENRE
  "like Titanic" is similar_to. "the actors from Titanic" is a reference. "a heist movie" is topics
  [heist], not genre Crime.

PACKS AND PICKS
  The index lists every film covered: not on it means not covered. When the sentence asks HOW to watch
  a film it names (an edition, a language, a price, a quality), call load_film with its name to read
  its pack: what exists for that film and nothing else. Then add a pick: the film's m<n>, the family's
  f<n>, and a value for EVERY wish the sentence has (edition, quality, audio, sound), copied from what
  the family lists ("the long version" is the extended edition the pack names). A wish the family does
  not list is still written, as the viewer said it: code says what does not exist, never you. Point,
  never copy: no offer id, no price. Also fill the watch fields as usual."""

TOOLS = [{"type": "function", "function": {
    "name": "load_film",
    "description": "Load the packs of films named in the sentence: every way each can be watched.",
    "parameters": {"type": "object", "additionalProperties": False,
                   "properties": {"names": {"type": "array", "items": {"type": "string"}}},
                   "required": ["names"]},
    "strict": True}}]


class Session:
    """What code holds for one request: the refs, the loaded packs. Never the model."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.refs = {f"m{i}": f["id"] for i, f in enumerate(catalog.films, start=1)}
        self.ref_of = {fid: ref for ref, fid in self.refs.items()}
        self.loaded = {}  # film id -> (text, families), oldest first
        self.trace = []

    def index(self):
        return "\n".join(index_line(self.ref_of[f["id"]], f, len(self.catalog.offers.get(f["id"], [])))
                         for f in self.catalog.films)

    def load(self, names):
        out = []
        for name in names:
            if name.strip() in self.refs:  # an index ref: the model pointing, not naming
                film = self.catalog.by_id[self.refs[name.strip()]]
                name = f"{film['title']} ({film['year']})"
            year = re.search(r"\((\d{4})\)\s*$", name)
            title = name[:year.start()].strip() if year else name
            match, others = self.catalog.film(title, int(year.group(1)) if year else None)
            if not match or match.band == "unsure":
                out.append(f"'{name}': not in the catalogue")
                self.trace.append(f"load_film('{name}') -> not in the catalogue")
                continue
            film = self.catalog.by_id[match.key]
            text, families = pack(film, self.catalog.offers.get(film["id"], []))
            self.loaded.pop(film["id"], None)
            self.loaded[film["id"]] = (text, families)
            while len(self.loaded) > SLOTS:
                self.loaded.pop(next(iter(self.loaded)))
            also = [f"{self.ref_of[o.key]} {self.catalog.by_id[o.key]['title']} ({self.catalog.by_id[o.key]['year']})"
                    for o in others]
            note = f"\n(other films called that: {', '.join(also)})" if also else ""
            out.append(f"{self.ref_of[film['id']]} {text}{note}")
            self.trace.append(f"load_film('{name}') -> {self.ref_of[film['id']]} {film['title']} ({film['year']}), "
                              f"{len(families)} families" + (f"; also {', '.join(also)}" if also else ""))
        return "\n\n".join(out)


def instructions(session):
    genres = ", ".join(session.catalog.genres)
    return (f"Turn a viewer's sentence about what to watch into search parameters.\n\n"
            f"THE FIELDS\n{listing(SEARCH)}\n  picks{' ' * 16}pointers into a loaded pack, see PACKS AND PICKS\n\n"
            f"GENRES, use these words exactly: {genres}\n\n{RULES}\n\n"
            f"THE INDEX, every film covered\n{session.index()}\n\n{DICTIONARY}")


def answer_schema():
    query = schema(SEARCH, {"label": {"type": "string"}})
    return {"type": "object", "additionalProperties": False,
            "properties": {"queries": {"type": "array", "items": query}, "picks": PICK},
            "required": ["queries", "picks"]}


def ask(sentence, session, max_turns=4):
    messages = [{"role": "system", "content": instructions(session)}, {"role": "user", "content": sentence}]
    usage = []
    for _ in range(max_turns):
        message, used = chat(messages, schema=answer_schema(), tools=TOOLS)
        usage.append(used)
        if not message.get("tool_calls"):
            return json.loads(message["content"]), usage
        messages.append(message)
        for call in message["tool_calls"]:
            names = json.loads(call["function"]["arguments"])["names"]
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": session.load(names)})
    raise SystemExit("The model kept asking for packs without answering.")
