from lib.meccg.jsonl import read_all_jsonl


def show_stats(*attributes, cards=None, show_total=True):
    """
    Show stats for the cards that we've imported
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
