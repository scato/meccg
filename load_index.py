import json

from meccg.scraping import load_html
from meccg.unjinja import untemplate

load_html('http://meccg.net/netherlands/meccg/spoilers/')
index = untemplate('var/templates/index.jinja', 'var/html/index.html')
with open('var/json/index.json', 'w') as fp:
    json.dump(index, fp, indent='  ')
