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

        if file_name == 'atscreatnew.html':
            print(f'Skipping {file_name}')
            continue

        print(f'loading {file_name}')

        load_html(f'http://meccg.net/netherlands/meccg/spoilers/{file_name}')
        spoiler = None
        for template_file in glob('var/templates/*.jinja'):
            try:
                spoiler = untemplate(template_file, f'var/html/{file_name}')
            except Exception as e:
                print(e)

            if spoiler is not None:
                print(f'Parsed using {template_file}')
                break

        if spoiler is None:
            raise Exception(f'Could not parse {file_name}')

        cards = [
            {
                **{k: v for k, v in spoiler.items() if k != 'cards'},
                **{k: v for k, v in card.items() if not k.startswith('_')},
            }
            for card in spoiler['cards']
        ]
        dump_jsonl(f'var/jsonl/{base_name}.jsonl', cards)

    exit(0)

    with open('var/templates/wizcharacters.jinja') as fp:
        p = load_template(''.join(fp))

    with open('var/html/wizcharacters.html') as fp:
    # with open('var/html/wizards.html') as fp:
        m = p(
            ''.join(fp)
        )

    for c in m['characters']:
        print(c)
