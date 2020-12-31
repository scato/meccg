import yaml

from lib.meccg.scraping import load_html
from lib.meccg.jsonl import load_wizcharacters, load_dmcharacters, load_lecharacters, load_atscharacters, \
    load_whcharacters

if __name__ == '__main__':
    jsonl_loaders = {
        'wiz': load_wizcharacters,
        'dm': load_dmcharacters,
        'le': load_lecharacters,
        'ats': load_atscharacters,
        'wh': load_whcharacters,
    }

    with open('sources.yaml') as fp:
        for source in yaml.load(fp, Loader=yaml.SafeLoader):
            load_html(source['html'])
            jsonl_loaders[source['jsonl']]('var/html/' + source['html'].split('/')[-1])
