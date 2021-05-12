import json
import re
import traceback

from meccg.medea import Session


def next_statement(commands):
    match = re.match(r'^((?:[^";]|"(?:[^\\"]|\\.)*")*;)(.*)$', commands)
    if match:
        return match[1], match[2]
    else:
        return None, commands


def repl(initialization_query=None):
    session = Session()
    if initialization_query is not None:
        session.query(initialization_query)
    commands = ""
    while True:
        try:
            commands += input('medea> ') + '\n'
        except EOFError:
            break

        while True:
            statement, commands = next_statement(commands)
            if statement is None:
                break
            try:
                result = session.query(statement)
                if result is not None:
                    for row in result:
                        print(json.dumps(row, indent='  '))
            except Exception:
                traceback.print_exc()
