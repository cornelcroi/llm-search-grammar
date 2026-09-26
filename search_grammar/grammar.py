"""The search grammar: every field a person can mean, in one place.

A field is what it means (in the words the model reads), its JSON shape, and a STATUS:

    ready       code applies it today
    dictionary  the model returns a neutral fact ("age 6"); code holds the local knowledge
                (what a 6-year-old may watch here). The model never names a code or a rule.
    later       understood and parsed, not applicable yet. Code reports it with the reason,
                so nothing a person asked for is silently dropped.

The grammar is deliberately WIDER than what the system can do. The model parses everything a
person might want; only code, which knows the data, says what can be applied.

The prompt's field list and the strict JSON schema are both generated from the grammar, so they
cannot drift apart. There is no field for "unsupported": the model never reports failure.
"""
from dataclasses import dataclass

READY, DICTIONARY, LATER = "ready", "dictionary", "later"


@dataclass(frozen=True)
class Field:
    says: str
    shape: dict
    status: str = READY
    why: str | None = None  # a `later` field says why it cannot run yet


def words(description=""):
    shape = {"type": "array", "items": {"type": "string"}}
    return shape | ({"description": description} if description else {})


def number():
    return {"type": ["integer", "null"]}


def one_of(*values):
    return {"type": ["string", "null"], "enum": [*values, None]}


def listing(fields):
    """The grammar as the model reads it: one line per field."""
    width = max(len(name) for name in fields) + 2
    return "\n".join(f"  {name:<{width}}{f.says}" for name, f in fields.items())


def schema(fields, extra=None):
    """A strict JSON schema object: every field required, nothing else allowed."""
    properties = {name: f.shape for name, f in fields.items()} | (extra or {})
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def problems(fields, prompt, handler_source):
    """What makes a grammar lie. Run it in tests; an empty list means grammar, prompt and code agree.

    - a ready or dictionary field no code handles parses correctly and then vanishes: confident
      results for half a sentence
    - a later field with no reason cannot be reported honestly
    - a field the prompt never mentions is required by the schema and explained nowhere
    """
    found = []
    for name, f in fields.items():
        if f.status in (READY, DICTIONARY) and f'"{name}"' not in handler_source:
            found.append(f"{name}: declared {f.status}, handled nowhere")
        if f.status == LATER and not f.why:
            found.append(f"{name}: later, but no reason given")
        if name not in prompt:
            found.append(f"{name}: in the schema, not explained in the prompt")
    return found
