import re
from os import system

from meccg.jsonl import read_all_jsonl


system("python.exe load2.py")


def is_required(attribute, card):
    if attribute in ['name', 'set', 'type', 'alignment']:
        return True
    elif attribute in ['class']:
        return card['type'] in ['Hazard', 'Resource']
    elif attribute in ['skills']:
        return card['type'] in ['Character']
    elif attribute in ['site_type', 'region']:
        return card['type'] in ['Site']
    elif attribute in ['region_type']:
        return card['type'] in ['Region']
    else:
        return False


def is_nullable(attribute):
    return attribute not in ['set', 'category', 'type', 'site_type', 'region', 'region_type']


ATTRIBUTES = [
    'set', 'category',
    'type', 'alignment',
    'mp', 'site_type', 'region_type', 'name',
    'class', 'race', 'skills', 'region',
]

for attribute in ATTRIBUTES:
    patterns = []
    with open(f'var/regex/{attribute}.txt', encoding='UTF-8') as fp:
        for pattern in fp:
            patterns.append(f'^{pattern.strip()}$')

    passed = 0
    total = 0
    example = None
    for card in read_all_jsonl():
        if attribute not in card:
            if is_required(attribute, card):
                total += 1
                if example is None:
                    example = f'attribute is missing ({card["set"]}, {card["category"]})'
        elif card[attribute] is None:
            if not is_nullable(attribute):
                total += 1
                if example is None:
                    example = f'attribute is None ({card["set"]}, {card["category"]})'
        elif attribute == 'skills':
            total += 1
            if isinstance(card[attribute], list):
                if all(
                    any(re.match(pattern, skill) for pattern in patterns)
                    for skill in card[attribute]
                ):
                    passed += 1
                elif example is None:
                    example = f'{card[attribute]} contains invalid item ({card["set"]}, {card["category"]})'
            elif example is None:
                example = f'{card[attribute]} is not a list ({card["set"]}, {card["category"]})'
        else:
            total += 1
            if any(re.match(pattern, card[attribute]) for pattern in patterns):
                passed += 1
            elif example is None:
                example = f'{card[attribute]} ({card["set"]}, {card["category"]})'

    print(f'{attribute} {passed}/{total}')

    if example is not None:
        print(f'there were failures for attribute "{attribute}"')
        print(f'example: {example}')
