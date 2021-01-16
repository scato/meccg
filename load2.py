import re

import yaml

from lib.meccg.scraping import load_html
from lib.meccg.jsonl import dump_jsonl
from lib.meccg.unjinja import untemplate


def dump_all(template_whitelist=None):
    file_blacklist = ('atscreatnew.html', 'empty.html', 'german.html')
    two_letter_template_names = ('dm', 'le', 'wh')

    with open('sets.yaml') as fp:
        sets = yaml.load(fp, Loader=yaml.SafeLoader)

    load_html('http://meccg.net/netherlands/meccg/spoilers/')
    index = untemplate('var/templates/index.jinja', 'var/html/index.html')
    dump_jsonl('var/jsonl/index.jsonl', index['files'])

    for file in index['files']:
        encoding = None
        file_name = file["name"]
        base_name = file_name.replace('.html', '')
        if file_name[0:2] in two_letter_template_names:
            template_name = file_name[0:2] + '.jinja'
        else:
            template_name = file_name[0:3] + '.jinja'

        if file_name in file_blacklist:
            print(f'Skipping {file_name}')
            continue

        if template_whitelist is not None and template_name not in template_whitelist:
            print(f'Skipping {file_name}')
            continue

        if file_name in ('lecreatures.html', 'lefactions.html', 'leitems.html', 'lemevents.html', 'leminions.html',
                         'leringwraith.html'):
            encoding = 'mac_roman'

        print(f'loading {file_name} using {template_name}')

        load_html(f'http://meccg.net/netherlands/meccg/spoilers/{file_name}')
        spoiler = untemplate(
            f'var/templates/{template_name}',
            f'var/html/{file_name}',
            encoding=encoding,
            # max_tries=1_000_000
        )

        if 'cards' in spoiler:
            def extra(card):
                if 'race' in card and card['race'] in sets[spoiler['set']][spoiler['category']]:
                    return sets[spoiler['set']][spoiler['category']][card['race']]
                else:
                    return sets[spoiler['set']][spoiler['category']]
            # TODO: check op callable weghalen, template moet eenduidig zijn!
            cards = [
                {
                    **{k: v for k, v in spoiler.items() if k != 'cards' and not callable(v)},
                    **{k: v for k, v in extra(card).items()},
                    **{k: v for k, v in card.items() if not k.startswith('_') and not callable(v)},
                }
                for card in spoiler['cards']
            ]
        else:
            cards = [
                {
                    **{k: v for k, v in spoiler.items() if k != 'sets' and not callable(v)},
                    **{k: v for k, v in set.items() if k != 'cards' and not callable(v)},
                    **{k: v for k, v in sets[set['set']][spoiler['category']].items()},
                    **{k: v for k, v in card.items() if not k.startswith('_') and not callable(v)},
                }
                for set in spoiler['sets']
                for card in set['cards']
            ]

        for card in cards:
            if card['name'] == 'Dôgrib':
                card['mp'] = ''
                card['mind'] = '2'

            if card['name'] == 'Bill Ferny' and card['category'] == 'Promo Cards':
                card['prowess'] = '2'
                card['body'] = '8'

            if card['name'] == 'Barrow-wight' and card['set'] == 'The Lidless Eye':
                card['body'] = '-'

            if card['name'] == 'Goblin-faces':
                card['body'] = '-'

            if card['name'] == 'The White Hand':
                card['body'] = '-'

            if card['type'] == 'Character' or card['type'] == 'Hazard' and card['class'] == 'Agent':
                if 'mp' not in card or card['mp'] is None or card['mp'] == '0':
                    card['mp'] = ''
                if 'mind' not in card or card['mind'] == '' or card['mind'] == '0':
                    card['mind'] = None
                if 'gi' not in card:
                    card['gi'] = None
                if card['set'] == 'Dark Minions' and card['category'] != 'Promo Cards':
                    card['home_site'] = [
                        home_site.replace('\n', ' ').strip()
                        for home_site in card['home_site'].split(',')
                    ]
                elif card['set'] == 'The White Hand':
                    card['home_site'] = [
                        home_site.replace('\n', '')
                        for home_site in card['home_site']
                    ]
                if 'cp' not in card or card['cp'] == '' or card['cp'] == '0':
                    card['cp'] = None
                if isinstance(card['text'], list):
                    card['text'] = ''.join(card['text'])
                card['text'] = card['text'].replace('\n', ' ')
                card['text'] = card['text'].replace('  ', ' ')
                card['text'] = re.sub(r'(\."?) *', r'\1\n', card['text'])
                card['text'] = card['text'].split('\n')
                if card['text'][-1] == '':
                    card['text'] = card['text'][:-1]
                else:
                    card['text'][-1] += '.'
            else:
                if 'mind' in card and card['mind'] in ('', '0'):
                    card['mind'] = None
                if 'cp' in card and card['cp'] in ('', '0'):
                    card['cp'] = None
                if 'text' in card:
                    # TODO: remove this in the end; for now it's just to make validation easier
                    card['text'] = None

        dump_jsonl(f'var/jsonl/{base_name}.jsonl', cards)


dump_all()
# dump_all(('bal.jinja',))
