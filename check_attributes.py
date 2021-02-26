import inspect
import json
import re
import subprocess
import textwrap
from functools import lru_cache

from jsonschema import validate, ValidationError
import yaml

from meccg.jsonl import read_all_jsonl


@lru_cache
def get_patterns(card_type, card_class, attribute):
    patterns = []

    if attribute == 'text':
        if card_type == 'Character':
            patterns_filename = f'var/regex/{attribute}.character.txt'
        elif card_type == 'Hazard':
            if card_class == 'Agent':
                patterns_filename = f'var/regex/{attribute}.hazard-agent.txt'
            elif 'Creature' in card_class:
                patterns_filename = f'var/regex/{attribute}.hazard-creature.txt'
            else:
                patterns_filename = f'var/regex/{attribute}.hazard-event.txt'
        elif card_type == 'Resource':
            patterns_filename = f'var/regex/{attribute}.resource.txt'
        elif card_type == 'Site':
            return ['.*']
        elif card_type == 'Region':
            return ['.*']
    else:
        patterns_filename = f'var/regex/{attribute}.txt'

    with open(patterns_filename, encoding='UTF-8') as fp:
        for pattern in fp:
            if not pattern.startswith('#'):
                patterns.append(f'^{pattern.strip()}$')

    return patterns


def check_all(attributes):
    for attribute in attributes:
        passed = 0
        total = 0
        example = None

        for card in read_all_jsonl():
            patterns = get_patterns(card.get('type'), card.get('class'), attribute)

            if attribute not in card or card[attribute] is None:
                continue
            elif attribute in ('skills', 'home_site', 'text'):
                total += 1
                if isinstance(card[attribute], list):
                    if all(
                        any(re.match(pattern, value) for pattern in patterns)
                        for value in card[attribute]
                    ):
                        passed += 1
                    elif example is None:
                        first_mismatch = next(
                            value
                            for value in card[attribute]
                            if not any(re.match(pattern, value) for pattern in patterns)
                        )
                        example = f'{card[attribute]} contains invalid item {first_mismatch} ({card["set"]} - {card["name"]})'
                elif example is None:
                    example = f'{card[attribute]} is not a list ({card["set"]} - {card["name"]})'
            else:
                total += 1
                if any(re.match(pattern, card[attribute]) for pattern in patterns):
                    passed += 1
                elif example is None:
                    example = f'{card[attribute]} ({card["set"]} - {card["name"]})'

        print(f'{attribute} {passed}/{total}')

        if example is not None:
            print(f'there were failures for attribute "{attribute}"')
            print(f'example: {example}')
            exit(1)


def print_all(attribute):
    values = sorted(set(
        value
        for card in read_all_jsonl()
        if attribute in card and card[attribute] is not None
        for value in (card[attribute] if isinstance(card[attribute], list) else [card[attribute]])
    ))
    for value in values:
        print(value)


def check_schema(filename):
    with open(filename) as fp:
        schema = json.load(fp)

    for card in read_all_jsonl():
        try:
            if card['type'] == 'Character':
                validate(instance=card, schema=schema['definitions']['common'])
                validate(instance=card, schema=schema['definitions']['character']['allOf'][1])
            elif card['type'] == 'Hazard' and card['class'] == 'Agent':
                validate(instance=card, schema=schema['definitions']['common'])
                validate(instance=card, schema=schema['definitions']['hazard-agent']['allOf'][1])
            elif card['type'] == 'Hazard' and 'Creature' in card['class']:
                validate(instance=card, schema=schema['definitions']['common'])
                validate(instance=card, schema=schema['definitions']['hazard-creature']['allOf'][1])
        except ValidationError as error:
            print(yaml.dump(card, Dumper=yaml.Dumper, allow_unicode=True))
            print(error)
            exit(1)


def check_rule(rule, cards):
    rule_string = inspect.getsource(rule)
    rule_string = textwrap.dedent(rule_string)
    rule_string = re.sub(r'^\s*lambda cards: (.*),\s*$', r'\1', rule_string, flags=re.DOTALL)
    print(rule_string, end='... ')
    last_card = None
    result = rule((last_card := card) for card in cards)
    if result:
        print('OK')
    else:
        print('FAIL')
        print()
        print(yaml.dump(last_card, Dumper=yaml.Dumper, allow_unicode=True))
    return result


def check_rules(rules):
    cards = list(read_all_jsonl())
    for rule in rules:
        result = check_rule(rule, cards)
        if not result:
            exit(1)


RULES = [
    # CHARACTERS
    lambda cards: all(
        card['mp'] == ''
        for card in cards
        if card['type'] == 'Character' and card['race'] in ('Balrog', 'Ringwraith', 'Fallen-wizard', 'Wizard')
    ),
    lambda cards: all(
        card['mp'] == ''
        for card in cards
        if card['type'] == 'Character' and card['mind'] in ('1', '2')
    ),
    lambda cards: all(
        card['mp'] == '1'
        for card in cards
        if card['type'] == 'Character' and card['mind'] in ('3', '4')
    ),
    lambda cards: all(
        card['mp'] == '2'
        for card in cards
        if card['type'] == 'Character' and card['mind'] in ('5', '6', '7')
    ),
    lambda cards: all(
        card['mp'] == '3'
        for card in cards
        if card['type'] == 'Character' and card['mind'] in ('8', '9', '10')
    ),
    lambda cards: all(
        card['mind'] is None
        for card in cards
        if card['type'] == 'Character' and card['race'] in ('Balrog', 'Ringwraith', 'Fallen-wizard', 'Wizard')
    ),
    lambda cards: all(
        card['mind'] is not None
        for card in cards
        if card['type'] == 'Character' and card['race'] not in ('Balrog', 'Ringwraith', 'Fallen-wizard', 'Wizard')
    ),
    lambda cards: all(
        card['gi'] is not None
        for card in cards
        if card['type'] == 'Character' and card['race'] == 'Fallen-wizard'
    ),
    lambda cards: all(
        card['gi'] is None
        for card in cards
        if card['type'] == 'Character' and card['race'] != 'Fallen-wizard'
    ),
    lambda cards: all(
        card['di'] in ('0', '1', '2', '3', '4')
        for card in cards
        if card['type'] == 'Character' and card['race'] not in ('Balrog', 'Ringwraith', 'Fallen-wizard', 'Wizard')
    ),
    lambda cards: all(
        card['di'] in ('3', '4', '5', '6')
        for card in cards
        if card['type'] == 'Character' and card['race'] in ('Balrog', 'Ringwraith')
    ),
    lambda cards: all(
        card['di'] in ('5', '7', '9', '10', '12')
        for card in cards
        if card['type'] == 'Character' and card['race'] in ('Fallen-wizard', 'Wizard')
    ),
    lambda cards: all(
        len(card['skills']) == 2
        for card in cards
        if card['type'] == 'Character' and card['race'] == 'Balrog'
    ),
    lambda cards: all(
        len(card['skills']) in (1, 2, 3)
        for card in cards
        if card['type'] == 'Character' and card['race'] == 'Ringwraith'
    ),
    lambda cards: all(
        len(card['skills']) == 4
        for card in cards
        if card['type'] == 'Character' and card['race'] in ('Fallen-wizard', 'Wizard')
    ),
    lambda cards: all(
        'Unique.' in card['text']
        for card in cards
        if card['type'] == 'Character'
        and not (card['alignment'] == 'Minion' and card['race'] in ('Man', 'Orc', 'Troll'))
    ),
]

ATTRIBUTES = [
    'set', 'type', 'alignment',
    'mp', 'site_type', 'region_type', 'name',
    'mind', 'gi', 'di',
    'skills', 'race', 'class', 'region',
    'prowess', 'body', 'home_site', 'cp',
    # 'text',
]

# subprocess.run("python.exe load2.py", shell=True, check=True)
check_schema('var/schema.json')
# print_all('text')
# check_all(ATTRIBUTES)
# check_rules(RULES)
