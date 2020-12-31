from lib.meccg.scraping import load_html
from lib.meccg.jsonl import dump_jsonl
from lib.meccg.unjinja import untemplate

if __name__ == '__main__':
    template_whitelist = ('wiz.jinja',)
    file_blacklist = ('atscreatnew.html', 'empty.html', 'german.html')
    two_letter_template_names = ('dm', 'le', 'wh')

    load_html('http://meccg.net/netherlands/meccg/spoilers/')
    index = untemplate('var/templates/index.jinja', 'var/html/index.html')
    dump_jsonl('var/jsonl/index.jsonl', index['files'])

    for file in index['files']:
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

        print(f'loading {file_name} using {template_name}')

        load_html(f'http://meccg.net/netherlands/meccg/spoilers/{file_name}')
        spoiler = untemplate(f'var/templates/{template_name}', f'var/html/{file_name}', max_tries=100_000)

        if 'cards' in spoiler:
            # TODO: check op callable weghalen, template moet eenduidig zijn!
            cards = [
                {
                    **{k: v for k, v in spoiler.items() if k != 'cards' and not callable(v)},
                    **{k: v for k, v in card.items() if not k.startswith('_') and not callable(v)},
                }
                for card in spoiler['cards']
            ]
        else:
            cards = [
                {
                    **{k: v for k, v in spoiler.items() if k != 'sets' and not callable(v)},
                    **{k: v for k, v in set.items() if k != 'cards' and not callable(v)},
                    **{k: v for k, v in card.items() if not k.startswith('_') and not callable(v)},
                }
                for set in spoiler['sets']
                for card in set['cards']
            ]

        dump_jsonl(f'var/jsonl/{base_name}.jsonl', cards)
