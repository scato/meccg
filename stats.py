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
    Dark Minions:
      - Non-minion Agents (2)
      - Allies (3)
      - Characters (1)
      - Hazard Creatures (9)
      - Hazard Events (62)
      - Items (11)
      - Minion Agents (27)
      - Resource Events (52)
      - Sites (13)
      - Promo Cards (4)
    The Dragons:
      - Ally cards (1)
      - Character cards (5)
      - Faction cards (3)
      - Hazard Creature cards (28)
      - Hazard Event cards (61)
      - Item cards (18)
      - Resource Event cards (56)
      - Site cards (9)
      - Promo Cards (2)
    The Lidless Eye:
      - Allies (7)
      - Hazard Creatures (42)
      - factions (38)
      - Hazard Events (51)
      - Items (52)
      - Minion Resource Events (100)
      - Minions (49)
      - Ringwraiths (9)
      - Sites (69)
      - Promo Cards (2)
    The Wizards (Limited):
      - Promo Cards (4)
    The Wizards (Unlimited):
      - Promo Cards (1)
    The White Hand:
      - Characters (7)
      - Hazard Creatures (1)
      - Hazard Events (19)
      - Hero Resources (8)
      - Minion Resources (14)
      - Sites (4)
      - Stage Resources: General (31)
      - Stage Resources: Wizard Specific (33)
      - Fallen Wizards (5)
    The Wizards:
      - Ally cards (11)
      - Wizard cards (5)
      - Character cards (66)
      - Faction cards (29)
      - Hazard Creature cards (55)
      - Hazard Events cards (60)
      - Item cards (53)
      - Region cards (52)
      - Resource cards (87)
      - Site cards (69)
    Total (1677)
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

    total = 0
    for set, cards_in_set in cards.items():
        print(f'{set}:')
        for category, cards_in_category in cards_in_set.items():
            total += len(cards_in_category)
            print(f'  - {category} ({len(cards_in_category)})')

    print(f'Total ({total})')


show_stats()
