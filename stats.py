import os
from glob import glob

from lib.meccg.jsonl import read_jsonl


def show_stats():
    """
    Show stats for the cards that we've imported
    >>> show_stats()
    Against the Shadow:
      - Hazard Creatures (16)
      - Hazard Events (21)
      - Hero Resources (23)
      - Hero sites (6)
      - Minion Allies (6)
      - Minion Resource Events (33)
      - Minion Factions (15)
      - Minion Items (15)
      - Minions (6)
      - Minion Sites (28)
    The Balrog:
      - Character cards (8)
      - Hazard cards (19)
      - Heroes (4)
      - Hero Resource cards (7)
      - Minion Resource cards (10)
      - Balrog specific Resource cards (38)
      - Site cards (22)
    """
    cards = {}
    for file in glob('var/jsonl/*.jsonl'):
        if os.path.basename(file) != 'index.jsonl':
            for card in read_jsonl(file):
                if card['set'] not in cards:
                    cards[card['set']] = {}
                if card['category'] not in cards[card['set']]:
                    cards[card['set']][card['category']] = []
                cards[card['set']][card['category']].append(card)

    for set, cards_in_set in cards.items():
        print(f'{set}:')
        for category, cards_in_category in cards_in_set.items():
            print(f'  - {category} ({len(cards_in_category)})')


show_stats()
