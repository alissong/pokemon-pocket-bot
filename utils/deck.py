# src/deck.py
import json
import os

DECK_FILE = "deck.json"


def load_deck():
    if os.path.exists(DECK_FILE):
        with open(DECK_FILE) as f:
            return json.load(f)
    else:
        return {}


def save_deck(deck_info):
    with open(DECK_FILE, "w") as f:
        json.dump(deck_info, f, indent=4)


# Initialize deck_info
deck_info = load_deck()
