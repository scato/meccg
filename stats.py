from lib.meccg.jsonl import read_all_jsonl


def show_stats(*attributes, cards=None, show_total=True):
    """
    Show stats for the cards that we've imported
    >>> show_stats('set', 'category')
    Against the Shadow:
      - Hazard Creatures (16)
      - Hazard Events (21)
      - Hero Resources (23)
      - Hero sites (6)
      - Minion Allies (6)
      - Minion Factions (15)
      - Minion Items (15)
      - Minion Resource Events (33)
      - Minion Sites (28)
      - Minions (6)
    Dark Minions:
      - Allies (3)
      - Characters (1)
      - Hazard Creatures (9)
      - Hazard Events (62)
      - Items (11)
      - Minion Agents (27)
      - Non-minion Agents (2)
      - Promo Cards (4)
      - Resource Events (52)
      - Sites (13)
    The Balrog:
      - Balrog specific Resource cards (38)
      - Character cards (8)
      - Hazard cards (19)
      - Hero Resource cards (7)
      - Heroes (4)
      - Minion Resource cards (10)
      - Site cards (22)
    The Dragons:
      - Ally cards (1)
      - Character cards (5)
      - Faction cards (3)
      - Hazard Creature cards (28)
      - Hazard Event cards (61)
      - Item cards (18)
      - Promo Cards (2)
      - Resource Event cards (56)
      - Site cards (9)
    The Lidless Eye:
      - Allies (7)
      - Hazard Creatures (42)
      - Hazard Events (51)
      - Items (52)
      - Minion Resource Events (100)
      - Minions (49)
      - Promo Cards (2)
      - Ringwraiths (9)
      - Sites (69)
      - factions (38)
    The White Hand:
      - Characters (7)
      - Fallen Wizards (5)
      - Hazard Creatures (1)
      - Hazard Events (19)
      - Hero Resources (8)
      - Minion Resources (14)
      - Sites (4)
      - Stage Resources: General (31)
      - Stage Resources: Wizard Specific (33)
    The Wizards:
      - Ally cards (11)
      - Character cards (66)
      - Faction cards (29)
      - Hazard Creature cards (55)
      - Hazard Events cards (60)
      - Item cards (53)
      - Region cards (52)
      - Resource cards (87)
      - Site cards (69)
      - Wizard cards (5)
    The Wizards (Limited):
      - Promo Cards (4)
    The Wizards (Unlimited):
      - Promo Cards (1)
    Total (1677)
    >>> show_stats('type', 'alignment')
    Character:
      - Balrog (1)
      - Fallen-wizard (5)
      - Hero (74)
      - Minion (97)
      - Ringwraith (9)
      - Wizard (5)
    Hazard:
      - None (456)
    Region:
      - None (52)
    Resource:
      - Hero (364)
      - Minion (330)
      - Stage (64)
    Site:
      - Balrog (22)
      - Fallen-wizard (4)
      - Hero (97)
      - Minion (97)
    Total (1677)
    >>> show_stats('type', 'race')
    Character:
      - Balrog (1)
      - Dunadan (1)
      - Dwarf (7)
      - Dúnadan (8)
      - Dûnadan (1)
      - Elf (7)
      - Fallen-wizard (5)
      - Hobbit (2)
      - Man (40)
      - Orc (26)
      - Ringwraith (9)
      - Troll (13)
    Hazard:
      - Hobbit (2)
      - None (6)
    Region:
    Resource:
      - Animal (4)
      - Dragon (9)
      - Dunadan (4)
      - Dwarf (5)
      - Dúnadan (1)
      - Eagle (1)
      - Elf (2)
      - Ent (1)
      - Hobbit (1)
      - Man (39)
      - None (5)
      - Orc (20)
      - Special (1)
      - Troll (4)
      - Wolf (3)
      - Wose (3)
    Site:
    Total (231)
    """
    if cards is None:
        cards = list(read_all_jsonl())

    total = 0
    attribute = attributes[0]
    for value in sorted(set(str(card[attribute]) for card in cards if attribute in card)):
        cards_with_attribute = [card for card in cards if attribute in card and str(card[attribute]) == value]
        if len(attributes) > 1:
            print(f'{value}:')
            total += show_stats(*attributes[1:], cards=cards_with_attribute, show_total=False)
        else:
            num_cards_with_attribute = len(cards_with_attribute)
            total += num_cards_with_attribute
            print(f'  - {value} ({num_cards_with_attribute})')

    if show_total:
        print(f'Total ({total})')
    else:
        return total
