"""How much the compact grammar saves, measured with no model at all.

    python3 -m examples.movies.measure [film title]

On INVENTED offers: the ratios illustrate the mechanism, they are not a finding about real catalogues.
"""
import json
import statistics
import sys

from search_grammar.compact import tokens
from examples.movies.offers import DICTIONARY, index_line, load, pack, raw_line


def main():
    films, by_film = load()
    all_offers = [o for offers in by_film.values() for o in offers]

    raw_text = "\n".join(raw_line(o) for o in all_offers)
    raw_json = json.dumps(all_offers)
    index = "\n".join(index_line(f"m{i}", f, len(by_film.get(f["id"], []))) for i, f in enumerate(films, start=1))
    packs = {f["id"]: pack(f, by_film[f["id"]]) for f in films if by_film.get(f["id"])}
    pack_tokens = [tokens(text) for text, _ in packs.values()]
    offer_counts = [len(by_film[fid]) for fid in packs]
    family_counts = [len(families) for _, families in packs.values()]

    print(f"{len(films)} films, {len(all_offers):,} offers (invented) · tokens estimated at 4 characters each\n")
    print("Everything, the naive way")
    print(f"  as JSON                        {tokens(raw_json):>9,} tokens")
    print(f"  one line per offer             {tokens(raw_text):>9,} tokens")
    print("\nThe grammar")
    print(f"  index, one line per film       {tokens(index):>9,} tokens   always in the prompt")
    print(f"  dictionary, written once       {tokens(DICTIONARY):>9,} tokens   always in the prompt, cached")
    print(f"  one pack, median               {statistics.median(pack_tokens):>9,.0f} tokens   sent when the sentence names the film")
    print(f"  offers per film, median        {statistics.median(offer_counts):>9,.0f}  -> families {statistics.median(family_counts):.0f}")
    print(f"  offers per family, overall     {sum(offer_counts) / sum(family_counts):>9,.1f}")

    context = tokens(index) + tokens(DICTIONARY) + 2 * statistics.median(pack_tokens)
    print(f"\nA request with two films loaded  {context:>9,.0f} tokens, "
          f"against {tokens(raw_text):,} to carry every offer")

    if len(sys.argv) > 1:
        wanted = " ".join(sys.argv[1:]).lower()
        for f in films:
            if f["title"].lower() == wanted and f["id"] in packs:
                text, _ = packs[f["id"]]
                raw = "\n".join(raw_line(o) for o in by_film[f["id"]])
                print(f"\n{text}\n\n({tokens(text)} tokens, against {tokens(raw)} for its {len(by_film[f['id']])} raw offers)")


if __name__ == "__main__":
    main()
