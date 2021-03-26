import glob
import json
import os

from meccg.scraping import load_html
from meccg.unjinja import untemplate

file_blacklist = ('atscreatnew', 'balhazcreatures', 'empty', 'german')
mac_roman_files = ('lecreatures', 'lefactions', 'leitems', 'lemevents', 'leminions', 'leringwraith', 'whwiz')

templates = {
    os.path.splitext(os.path.basename(filename))[0]: filename
    for filename in glob.glob('var/templates/*.jinja')
}

with open('var/json/index.json') as fp:
    index = json.load(fp)

for file in index['files']:
    name = os.path.splitext(file["name"])[0]
    if name not in file_blacklist:
        for prefix, template in templates.items():
            if name.startswith(prefix):
                encoding = 'mac_roman' if name in mac_roman_files else None
                load_html(f'http://meccg.net/netherlands/meccg/spoilers/{name}.html')
                spoiler = untemplate(template, f'var/html/{name}.html', encoding=encoding)
                with open(f'var/json/{name}.json', 'w') as fp:
                    json.dump(spoiler, fp, indent='  ')
