import json
import re

from meccg.medea import Session


def next_statement(commands):
    match = re.match(r'^((?:[^";]|"(?:[^\\"]|\\.)*")*;)(.*)$', commands)
    if match:
        return match[1], match[2]
    else:
        return None, commands


def repl():
    session = Session()
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
            result = None
            try:
                result = session.query(statement)
            except Exception as ex:
                print(ex)
            if result is not None:
                for row in result:
                    print(json.dumps(row, indent='  '))
