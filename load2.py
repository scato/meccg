from glob import glob

from lib.meccg.html import load_html
from lib.meccg.jsonl import dump_jsonl
from lib.meccg.unjinja import load_template, untemplate

if __name__ == '__main__':
    load_html('http://meccg.net/netherlands/meccg/spoilers/')
    index = untemplate('var/templates/index.jinja', 'var/html/index.html')
    dump_jsonl('var/jsonl/index.jsonl', index['files'])

    for file in index['files']:
        file_name = file["name"]
        base_name = file_name.replace('.html', '')
        template_name = file_name[0:3] + '.jinja'
        template_file = f'var/templates/{template_name}'

        if file_name == 'atscreatnew.html' or template_name != 'bal.jinja':
            print(f'Skipping {file_name}')
            continue

        if file_name == 'balhazcreatures.html':
            template_name = 'bal2.jinja'
            template_file = f'var/templates/{template_name}'

        print(f'loading {file_name} using {template_name}')

        load_html(f'http://meccg.net/netherlands/meccg/spoilers/{file_name}')
        spoiler = untemplate(template_file, f'var/html/{file_name}')

        cards = [
            {
                **{k: v for k, v in spoiler.items() if k != 'cards'},
                **{k: v for k, v in card.items() if not k.startswith('_')},
            }
            for card in spoiler['cards']
        ]

        if cards[0]['set'] == 'The Balrgo':
            for card in cards:
                card['set'] = 'The Balrog'

        dump_jsonl(f'var/jsonl/{base_name}.jsonl', cards)
