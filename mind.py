import itertools
import math

from lib.meccg.jsonl import read_jsonl

if __name__ == '__main__':
    characters = list(itertools.chain(
        read_jsonl('var/jsonl/wizards.jsonl'),
        read_jsonl('var/jsonl/wizcharacters.jsonl'),
        read_jsonl('var/jsonl/dracharacters.jsonl'),
        read_jsonl('var/jsonl/dmcharacters.jsonl'),
        read_jsonl('var/jsonl/dmminions.jsonl'),
        read_jsonl('var/jsonl/leringwraith.jsonl'),
        read_jsonl('var/jsonl/leminions.jsonl'),
        read_jsonl('var/jsonl/atsminions.jsonl'),
        read_jsonl('var/jsonl/whwiz.jsonl'),
        read_jsonl('var/jsonl/whchar.jsonl'),
        read_jsonl('var/jsonl/balcharacters.jsonl'),
    ))

    for character in characters:
        if character['MIND'] is None:
            actual_mind = None
        elif character['MIND'] == '':
            actual_mind = ''
        else:
            actual_mind = int(character['MIND'])
        calculated_mind = -3.5

        calculated_mind += int(character['INFLUENCE'])
        calculated_mind += len(character['SKILLS']) / 2
        calculated_mind += int(character['PROWESS']) / 2
        calculated_mind += int(character['BODY']) / 2

        if character['RACE'] == 'Hobbit':
            calculated_mind += 1.0
        elif character['RACE'] == 'Dwarf':
            if character['NAME'] not in ('Balin', 'Gimli', 'Kili', 'Oin', 'Thorin II'):
                calculated_mind -= 0.5
        elif character['HOME_SITE'] in ('Pelargir', 'Beorn\'s House'):
            calculated_mind -= 0.5
        elif character['HOME_SITE'] in ('Minas Tirith', 'Edoras'):
            if character['NAME'] not in ('Bergil', 'Denethor II', 'Eomer', 'Eowyn', 'Theoden'):
                calculated_mind -= 1.0

        if actual_mind != math.ceil(calculated_mind):
            print(character['NAME'], character['RACE'], actual_mind, calculated_mind)
