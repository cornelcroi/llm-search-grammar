"""Invent the watch offers for data/films.json: where, and how, each film can be watched.

    python3 scripts/generate_offers.py

THE OFFERS ARE INVENTED. The services are fictional, the prices made up. They exist to give every
film what a real offer has: tens to hundreds of options, different for each film, that no model
has ever seen. Generation is seeded by the film id, so the same catalogue always gives the same offers.

One offer is one way to watch: a service, a mode (subscription, rent, buy, free with ads), an
edition, a quality, an audio language and format, with the subtitles that come with it and a price.
"""
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Fictional services. `takes` decides which films a service carries.
SERVICES = {
    "StreamOne":    {"modes": ["subscription"], "takes": lambda f: f["year"] >= 1990, "odds": 0.55},
    "CinePass":     {"modes": ["subscription"], "takes": lambda f: True, "odds": 0.35},
    "ClassicVault": {"modes": ["subscription"], "takes": lambda f: f["year"] < 1980, "odds": 0.8},
    "NightOwl":     {"modes": ["subscription"],
                     "takes": lambda f: bool({"Thriller", "Horror", "Crime", "Mystery"} & set(f["genres"])), "odds": 0.6},
    "PopcornPlus":  {"modes": ["free"], "takes": lambda f: f["year"] <= 2013, "odds": 0.3},
    "RentBox":      {"modes": ["rent", "buy"], "takes": lambda f: True, "odds": 0.85},
    "FlixMarket":   {"modes": ["rent", "buy"], "takes": lambda f: f["year"] >= 1960, "odds": 0.6},
    "VidaStore":    {"modes": ["buy"], "takes": lambda f: True, "odds": 0.4},
}
PRICES = {  # mode -> quality -> list of possible prices, in euros
    "rent": {"SD": [2.49, 2.99], "HD": [3.49, 3.99], "4K": [4.99, 5.99]},
    "buy": {"SD": [5.99, 7.99], "HD": [9.99, 12.99], "4K": [14.99, 17.99]},
}
LANGUAGE_CODES = {"English": "en", "French": "fr", "German": "de", "Italian": "it", "Spanish": "es",
                  "Russian": "ru", "Japanese": "ja", "Arabic": "ar", "Portuguese": "pt", "Swedish": "sv"}
DUBS = ["fr", "en", "de", "es", "it"]


# Editions are named PER FILM: this is the vocabulary no model can know, and the reason a pack exists.
def editions_for(film, rng):
    names = ["theatrical"]
    director = (film["directors"] or ["the director"])[0].split()[-1]
    lead = (film["cast"] or [None])[0]
    age = 2026 - film["year"]
    if rng.random() < 0.3:
        names.append(f"{director}'s cut")
    if rng.random() < 0.3:
        names.append(f"extended (+{rng.randint(8, 40)} min)")
    anniversaries = [n for n in (20, 25, 30, 40, 50) if n <= age]
    if anniversaries and rng.random() < 0.3:
        names.append(f"{rng.choice(anniversaries)}th anniversary")
    if film["year"] >= 2008 and {"Action", "Adventure", "Science Fiction"} & set(film["genres"]) and rng.random() < 0.5:
        names.append("IMAX enhanced")
    if rng.random() < 0.4:
        person = lead if lead and rng.random() < 0.5 else (film["directors"] or [director])[0]
        names.append(f"with commentary by {person}")
    return names

AUDIO_FORMATS = {"SD": ["stereo"], "HD": ["stereo", "5.1"], "4K": ["5.1", "atmos"]}
SUBTITLES = ["fr", "en", "de", "es", "it", "pt", "nl", "pl", "ro", "ja"]


def qualities(film, mode, rng):
    available = ["SD", "HD"] + (["4K"] if film["year"] >= 2000 else [])
    if mode in ("subscription", "free"):
        return [rng.choice(available[1:] or available)] if mode == "subscription" else ["SD"]
    return available


def audio_languages(film, rng):
    original = LANGUAGE_CODES.get((film["languages"] or ["English"])[0], "en")
    dubs = [d for d in DUBS if d != original and rng.random() < (0.9 if d == "fr" else 0.5)]
    return [original] + dubs


def offers_for(film):
    rng = random.Random(film["id"])
    audio = audio_languages(film, rng)
    film_editions = editions_for(film, rng)
    offers = []
    for service, spec in SERVICES.items():
        if not spec["takes"](film) or rng.random() > spec["odds"]:
            continue
        # A service rarely carries every dub; each drops some.
        service_audio = [a for i, a in enumerate(audio) if i == 0 or rng.random() < 0.7]
        subtitles = sorted(rng.sample(SUBTITLES, rng.randint(3, len(SUBTITLES))))
        # Stores sell several editions of a well-known film; subscriptions carry one.
        store_editions = film_editions
        for mode in spec["modes"]:
            editions = store_editions if mode in PRICES else ["theatrical"]
            for edition in editions:
                for quality in qualities(film, mode, rng):
                    price = rng.choice(PRICES[mode][quality]) if mode in PRICES else 0.0
                    if edition != "theatrical" and price:
                        price = round(price + 1.0, 2)
                    for language in service_audio:
                        for sound in AUDIO_FORMATS[quality]:
                            offers.append({"film": film["id"], "service": service, "mode": mode,
                                           "edition": edition, "quality": quality, "audio": language,
                                           "sound": sound, "subtitles": subtitles, "price": price})
    return offers


def main():
    films = json.loads((DATA / "films.json").read_text())
    offers = [o for film in films for o in offers_for(film)]
    for i, offer in enumerate(offers, start=1):
        offer["id"] = f"of{i}"
    (DATA / "offers.json").write_text(json.dumps(offers, ensure_ascii=False) + "\n")
    per_film = [sum(1 for o in offers if o["film"] == f["id"]) for f in films]
    print(f"{len(offers)} invented offers for {len(films)} films: "
          f"min {min(per_film)}, median {sorted(per_film)[len(per_film) // 2]}, max {max(per_film)} per film")


if __name__ == "__main__":
    main()
