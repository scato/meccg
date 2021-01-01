import json
import os
from collections import Callable
from glob import glob

from bs4 import BeautifulSoup, NavigableString


def load_jsonl(html_filename, lines_to_attributes, card_tag_name):
    jsonl_filename = html_filename.replace('html', 'jsonl')

    with open(html_filename) as fp_in, open(jsonl_filename, 'w') as fp_out:
        soup = BeautifulSoup(fp_in, 'html.parser')
        for card in soup.find_all(card_tag_name):
            lines = []

            for node in card.next_elements:
                if isinstance(node, NavigableString) and node.strip() != '':
                    lines.append(node.strip())
                elif card_tag_name(node) if isinstance(card_tag_name, Callable) else node.name == card_tag_name:
                    break

            attributes = lines_to_attributes(lines)

            json.dump(attributes, fp_out)
            fp_out.write('\n')


def load_wizcharacters(html_filename):
    def lines_to_attributes(lines):
        attributes = {
            'NAME': lines[0],
            'TEXT': '',
        }

        for line in lines[1:]:
            known_keys = ('TYPE', 'RARITY', 'RACE', 'SKILLS', 'HOME_SITE', 'CLASS', 'MP', 'MIND', 'INFLUENCE',
                          'PROWESS', 'BODY', 'CORRUPTION', 'CORRUPT', 'ARTIST', 'RANDOM#')
            if ':' in line and line.split(':')[0] in known_keys:
                key, value = map(lambda x: x.strip(), line.split(':'))
                if key == 'SKILLS':
                    attributes[key] = value.split('/')
                else:
                    attributes[key] = value
            else:
                attributes['TEXT'] = (attributes['TEXT'] + ' ' + line.strip().replace('\n', ' ')).strip()

        return attributes

    load_jsonl(html_filename, lines_to_attributes, card_tag_name='h2')


def load_dmcharacters(html_filename):
    def lines_to_attributes(lines):
        assert len(lines) == 5

        details = list(map(lambda x: x.strip(' []').replace('\n', ' '), lines[3].split(';')))

        assert len(details) in (5, 6)

        attributes = {
            'NAME': lines[0],
            'TEXT': lines[4].replace('\n', ' '),
            'TYPE': lines[1],
            'RACE': lines[2].split(' ')[1],
            'SKILLS': lines[2].split(' ')[0].split('/'),
            'HOME_SITE': details[-1].replace('Home Site: ', ''),
            'MP': int(details[1].replace(' character MP', '').replace(' character/kill MP', '')),
            'MIND': int(details[2].replace(' mind', '')),
            'INFLUENCE': int(details[3].replace(' direct influence', '')),
            'PROWESS': int(details[0].split('/')[0]),
            'BODY': int(details[0].split('/')[0]),
            'CORRUPTION': int(details[4].replace(' corruption mod', '')) if len(details) == 6 else 0,
        }

        return attributes

    load_jsonl(html_filename, lines_to_attributes, card_tag_name='h2')


def load_lecharacters(html_filename):
    def lines_to_attributes(lines):
        assert len(lines) in (6, 7, 8)

        attributes = {
            'NAME': lines[0],
            'TEXT': lines[-1].split(' Home Site: ')[0],
            'HOME_SITE': lines[-1].split(' Home Site: ')[1],
            'RARITY': lines[1],
            'MP': int(lines[2]) if len(lines) == 8 else 0,
            'MIND': int(lines[-5]) if len(lines) in (7, 8) else None,
            'INFLUENCE': int(lines[-4]),
            'PROWESS': int(lines[-3].split('/')[0]),
            'BODY': int(lines[-3].split('/')[1]),
            'SKILLS': lines[-2].split(' ')[0].split('/'),
            'RACE': lines[-2].split(' ')[1],
        }

        return attributes

    load_jsonl(html_filename, lines_to_attributes, card_tag_name='b')


def load_atscharacters(html_filename):
    def lines_to_attributes(lines):
        assert len(lines) == 9

        attributes = {
            'NAME': lines[0],
            'TEXT': lines[7],
            'HOME_SITE': lines[8].replace('Home Site: ', ''),
            'RARITY': lines[1],
            'MP': int(lines[2]),
            'MIND': int(lines[3]),
            'INFLUENCE': int(lines[4]),
            'PROWESS': int(lines[5].split('/')[0]),
            'BODY': int(lines[5].split('/')[1]),
            'SKILLS': lines[6].split(' ')[0].split('/'),
            'RACE': lines[6].split(' ')[1],
        }

        return attributes

    def card_tag_name(tag):
        return tag.name == 'tr' and 'align' in tag.attrs and len(tag.find_all('th')) == 0

    load_jsonl(html_filename, lines_to_attributes, card_tag_name=card_tag_name)


def load_whcharacters(html_filename):
    def lines_to_attributes(lines):
        assert len(lines) in (7, 8)

        details = {
            key.strip(): value.strip()
            for key, value in (
                line.split(':')
                for line in lines[1:-2]
            )
        }

        attributes = {
            'NAME': lines[0],
            'TEXT': lines[-1].replace('\n', '').split(' Home Site: ')[0],
            'RARITY': details['Rarity'],
            'RACE': lines[-2].split(' ')[1],
            'SKILLS': lines[-2].split(' ')[0].split('/'),
            'HOME_SITE': lines[-1].replace('\n', '').split(' Home Site: ')[1],
            'GI': int(details['GI']) if 'GI' in details else None,
            'MIND': int(details['Mind']) if 'Mind' in details else None,
            'INFLUENCE': int(details['DI']),
            'PROWESS': int(details['Pr/Bd'].split('/')[0]),
            'BODY': int(details['Pr/Bd'].split('/')[1]),
        }

        return attributes

    load_jsonl(html_filename, lines_to_attributes, card_tag_name='h2')


def read_jsonl(filename):
    with open(filename) as fp:
        for line in fp:
            yield json.loads(line)


def read_all_jsonl():
    for file in glob('var/jsonl/*.jsonl'):
        if os.path.basename(file) != 'index.jsonl':
            for card in read_jsonl(file):
                yield card


def dump_jsonl(filename, records):
    with open(filename, 'w') as fp:
        for record in records:
            json.dump(record, fp)
            fp.write('\n')
