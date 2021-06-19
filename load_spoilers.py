import glob
import json
import os
from multiprocessing import Pool

from meccg.scraping import load_html
from meccg.unjinja import untemplate


PARALLEL = True
FILE_BLACKLIST = ('atscreatnew', 'balhazcreatures', 'empty', 'german')
MAC_ROMAN_FILES = (
    'lecreatures', 'lefactions', 'lehevents', 'leitems', 'lemevents', 'leminions', 'leringwraith',
    'whhazevent', 'whwiz',
)


def parse_file(name, template):
    print(f'Parsing {name}.html using {template}...')
    encoding = 'mac_roman' if name in MAC_ROMAN_FILES else None
    load_html(f'http://meccg.net/netherlands/meccg/spoilers/{name}.html')
    spoiler = untemplate(template, f'var/html/{name}.html', encoding=encoding)
    with open(f'var/json/{name}.json', 'w') as fp:
        json.dump(spoiler, fp, indent='  ')


def main():
    templates = {
        os.path.splitext(os.path.basename(filename))[0]: filename
        for filename in glob.glob('var/templates/*.jinja')
    }

    with open('var/json/index.json') as fp:
        index = json.load(fp)

    tasks = []

    for file in index['files']:
        name = os.path.splitext(file["name"])[0]
        if name not in FILE_BLACKLIST:
            for prefix, template in templates.items():
                if name.startswith(prefix):
                    tasks.append((name, template))

    if PARALLEL:
        pool = Pool(4)
        pool.starmap(parse_file, tasks)
    else:
        for args in tasks:
            parse_file(*args)


if __name__ == '__main__':
    main()
