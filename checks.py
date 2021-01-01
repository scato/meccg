from lib.meccg.jsonl import read_all_jsonl
import re

cards = list(read_all_jsonl())

# Names do not contain weird characters
pattern = re.compile(r'^[ !"&\'(),\-?A-Za-zÔÛáâäéëíîóôúû’]*$')
assert all(pattern.match(card['name']) for card in cards)
