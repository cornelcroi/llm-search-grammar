# FLOWS.md

The index. One line per flow; open only the doc you need.
Each source file says in its first line which flow doc it implements (`FLOW-CRITICAL: implements flows/...`).
A change that alters a flow updates its doc in the same commit (`scripts/hooks/pre-commit` warns when it doesn't).

| Flow | What it covers | Main files |
|---|---|---|
| [`flows/search.md`](flows/search.md) | One sentence end to end: spot the films, one model call, resolve, query, explain | `assistant.py`, `resolve.py`, `explain.py`, `web.py` |
| [`flows/grammar.md`](flows/grammar.md) | The fields, their status (ready, dictionary, later), the prompt and schema generated from them | `grammar.py`, `fields.py` |
| [`flows/packs.md`](flows/packs.md) | Items with their own options: index, dictionary, packs, and the model's pointers checked by code | `compact.py`, `offers.py`, `picks.py` |
| [`flows/data.md`](flows/data.md) | Rebuilding the films, the invented offers, the posters, and the recorded model answers the tests replay | `scripts/*.py`, `tests/answers.json` |

The forgiving search (`search_grammar/forgiving.py`) serves two flows: spotting titles in `search`, resolving names in `search` and checking pointers in `packs`.
