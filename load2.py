import json
import re

import yaml
from bs4 import BeautifulSoup

from lib.meccg.scraping import load_html
from lib.meccg.jsonl import dump_jsonl
from lib.meccg.unjinja import untemplate


def dump_all(template_whitelist=None):
    file_blacklist = ('atscreatnew.html', 'balhazcreatures.html', 'empty.html', 'german.html')
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
                         'leringwraith.html', 'whwiz.html'):
            encoding = 'mac_roman'

        print(f'loading {file_name} using {template_name}')

        load_html(f'http://meccg.net/netherlands/meccg/spoilers/{file_name}')
        spoiler = untemplate(
            f'var/templates/{template_name}',
            f'var/html/{file_name}',
            encoding=encoding,
            # max_tries=1_000_000
        )

        with open(f'var/json/{base_name}.json', 'w') as fp:
            print(spoiler)
            json.dump(spoiler, fp, indent='  ')

        if 'cards' in spoiler:
            def extra(card):
                if 'race' in card and card['race'] in sets[spoiler['set']][spoiler['category']]:
                    return sets[spoiler['set']][spoiler['category']][card['race']]
                else:
                    return sets[spoiler['set']][spoiler['category']]
            # TODO: check op callable weghalen, template moet eenduidig zijn!
            cards = [
                {
                    **{k: v for k, v in spoiler.items() if k != 'cards' and not k.startswith('_') and not callable(v)},
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
            if card['category'] == 'Promo Cards':
                fix_pro_card(card)
            elif card['set'] == 'Against the Shadow':
                fix_ats_card(card)
            elif card['set'] == 'The Balrog':
                fix_bal_card(card)
            elif card['set'] == 'Dark Minions':
                fix_dm_card(card)
            elif card['set'] == 'The Dragons':
                fix_dra_card(card)
            elif card['set'] == 'The Lidless Eye':
                fix_le_card(card)
            elif card['set'] == 'The White Hand':
                fix_wh_card(card)
            elif card['set'] == 'The Wizards':
                fix_wiz_card(card)

            """
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
                elif card['set'] == 'Against the Shadow':
                    del card['keyed_to']
                elif card['set'] in ('The Dragons', 'The Wizards'):
                    del card['artist']
                    del card['random_number']
                elif card['category'] == 'Promo Cards':
                    del card['playable']
                if 'cp' not in card or card['cp'] == '' or card['cp'] == '0':
                    card['cp'] = None
            elif card['type'] == 'Hazard' and 'Creature' in card['class']:
                if 'cp' in card and card['cp'] in ('', '0'):
                    del card['cp']
                if 'keyed_to' not in card:
                    pass
                elif card['keyed_to'] is None:
                    card['keyed_to'] = []
                else:
                    card['keyed_to'] = ':'.join(card['keyed_to']) \
                        .replace('Ruins:&:Lairs', 'Ruins & Lairs').split(':')
                    card['keyed_to'] = [
                        SITE_REGION_TYPE_MAPPING[x] if x in SITE_REGION_TYPE_MAPPING else x
                        for x in card['keyed_to']
                    ]
            else:
                if 'mind' in card and card['mind'] in ('', '0'):
                    card['mind'] = None
                if 'cp' in card and card['cp'] in ('', '0'):
                    card['cp'] = None
            """

        dump_jsonl(f'var/jsonl/{base_name}.jsonl', cards)


def fix_text(card):
    card['text'] = card['text'].replace('\n', ' ')
    card['text'] = card['text'].replace('  ', ' ')
    card['text'] = re.sub(r'(\."?) *', r'\1\n', card['text'])
    card['text'] = card['text'].split('\n')
    if card['text'][-1] == '':
        card['text'] = card['text'][:-1]
    else:
        card['text'][-1] += '.'


def fix_non_empty(attribute, card):
    if card[attribute] == '':
        card[attribute] = None


def fix_non_zero(attribute, card):
    if card[attribute] == '0':
        card[attribute] = None


def fix_non_null(attribute, card):
    if card[attribute] is None:
        card[attribute] = ''


def fix_required(attribute, card):
    assert attribute not in card
    card[attribute] = None


def fix_disallowed(attribute, card):
    assert card[attribute] in (None, '', '0')
    del card[attribute]


def fix_ats_card(card):
    del card['category']
    del card['rarity']

    if card['type'] == 'Character':
        fix_required('gi', card)
        fix_disallowed('keyed_to', card)
        fix_required('cp', card)
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        fix_disallowed('home_site', card)
        fix_text(card)
    elif card['type'] == 'Resource' and card['class'] == 'Ally':
        pass
    elif card['type'] == 'Resource' and card['class'] == 'Faction':
        if card['alignment'] == 'Hero':
            fix_disallowed('cp', card)
    elif card['type'] == 'Resource' and 'Item' in card['class']:
        fix_non_empty('cp', card)
    elif card['type'] == 'Resource':
        if card['alignment'] == 'Hero':
            fix_non_empty('cp', card)


def fix_bal_card(card):
    del card['category']

    if card['type'] == 'Character':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_empty('mind', card)
        fix_required('gi', card)
        fix_non_empty('cp', card)
        fix_non_zero('cp', card)

        if card['line_without_br'] != '':
            card['text'] += [card['line_without_br']]
        del card['line_without_br']
        card['text'] = ''.join(card['text'])
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        del card['subclass']
        del card['strikes']
        if card['line_without_br'] != '':
            card['text'] += [card['line_without_br']]
        del card['line_without_br']
    elif card['type'] == 'Resource' and card['class'] == 'Ally':
        pass
    elif card['type'] == 'Resource' and card['class'] == 'Ally':
        pass
    elif card['type'] == 'Resource' and 'Item' in card['class']:
        pass
    elif card['type'] == 'Resource':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('cp', card)


def fix_dm_card(card):
    del card['category']

    if card['type'] == 'Character':
        fix_required('gi', card)
        if card['alignment'] == 'Minion':
            fix_required('cp', card)
        card['home_site'] = [
            home_site.replace('\n', ' ').strip()
            for home_site in card['home_site'].split(',')
        ]
        card['text'] = ''.join(card['text'])
        fix_text(card)
    elif card['type'] == 'Hazard' and card['class'] == 'Agent':
        card['home_site'] = [
            home_site.replace('\n', ' ').strip()
            for home_site in card['home_site'].split(',')
        ]


def fix_dra_card(card):
    del card['category']
    del card['rarity']
    del card['artist']
    del card['random_number']

    if card['name'] == 'Ireful Flames':
        card['class'] = 'Permanent-event'

    if card['type'] == 'Character':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_required('gi', card)
        fix_non_zero('cp', card)
        card['text'] = ''.join(card['text'])
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        del card['subclass']
        del card['strikes']
        fix_disallowed('cp', card)
    elif card['type'] == 'Hazard':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('cp', card)
    elif card['type'] == 'Resource' and card['class'] == 'Ally':
        fix_disallowed('cp', card)
    elif card['type'] == 'Resource' and card['class'] == 'Faction':
        fix_disallowed('mind', card)
        fix_disallowed('cp', card)
    elif card['type'] == 'Resource' and 'Item' in card['class']:
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('mind', card)
    elif card['type'] == 'Resource':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('mind', card)
        fix_non_zero('cp', card)


def fix_le_card(card):
    del card['category']
    del card['rarity']

    if card['name'] == 'Dôgrib':
        card['mp'] = ''
        card['mind'] = '2'

    if card['name'] == 'Barrow-wight':
        card['body'] = '-'

    if card['type'] == 'Character':
        if card['race'] == 'Ringwraith':
            card['mp'] = ''
            card['mind'] = None
        else:
            fix_non_empty('mind', card)
            fix_non_null('mp', card)
        fix_required('gi', card)
        fix_required('cp', card)
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        fix_text(card)


def fix_pro_card(card):
    card['set'] = 'Promo Cards'
    del card['category']

    if card['name'] == 'Bill Ferny':
        card['prowess'] = '2'
        card['body'] = '8'

    if card['type'] == 'Character':
        fix_required('gi', card)
        fix_disallowed('keyed_to', card)
        card['text'] = BeautifulSoup(card['text'], "html.parser").get_text()
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        fix_disallowed('race', card)
        fix_disallowed('mind', card)
        fix_disallowed('di', card)
        fix_disallowed('cp', card)
        fix_disallowed('home_site', card)
        card['text'] = BeautifulSoup(card['text'], "html.parser").get_text()
        fix_text(card)


def fix_wh_card(card):
    del card['category']
    del card['rarity']

    if card['name'] == 'Goblin-faces':
        card['body'] = '-'

    if card['name'] == 'The White Hand':
        card['body'] = '-'

    if card['type'] == 'Character':
        if card['race'] == 'Fallen-wizard':
            card['mp'] = ''
            card['mind'] = None
        else:
            fix_non_null('mp', card)
            fix_required('gi', card)
        card['home_site'] = [
            home_site.replace('\n', '')
            for home_site in card['home_site']
        ]
        fix_required('cp', card)
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        fix_text(card)


def fix_wiz_card(card):
    del card['category']
    del card['rarity']
    del card['artist']

    if card['name'] == 'Olog-hai (Trolls)':
        card['text'] = ['Trolls.  Three strikes.']

    if card['type'] == 'Character':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('mind', card)
        fix_required('gi', card)
        fix_non_zero('cp', card)
        del card['random_number']
        card['text'] = ''.join(card['text'])
        fix_text(card)
    elif card['type'] == 'Hazard' and 'Creature' in card['class']:
        del card['subclass']
        del card['strikes']
        fix_disallowed('cp', card)
        card['keyed_to'] = list(card['keyed_to'])
        del card['random_number']
    elif card['type'] == 'Hazard':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('cp', card)
    elif card['type'] == 'Resource' and card['class'] == 'Ally':
        fix_disallowed('cp', card)
    elif card['type'] == 'Resource' and card['class'] == 'Faction':
        fix_disallowed('mind', card)
        fix_disallowed('cp', card)
    elif card['type'] == 'Resource' and 'Item' in card['class']:
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('mind', card)
        fix_non_zero('cp', card)
    elif card['type'] == 'Resource':
        fix_non_zero('mp', card)
        fix_non_null('mp', card)
        fix_non_zero('mind', card)
        fix_non_zero('cp', card)


SITE_REGION_TYPE_MAPPING = {
    'Free-hold': 'F',
    'Border-hold': 'B',
    'Ruins & Lairs': 'R',
    'Free-domain': 'f',
    'Wilderness': 'w',
    'Border-land': 'b',
}


dump_all()
# dump_all(('wiz.jinja',))
