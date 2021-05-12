from meccg.repl import repl

repl('''
    LOAD JSONL FROM `var/jsonl/${source}.jsonl` AS card
    CREATE card;
''')
