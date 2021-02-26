"""
>>> pprint(parser.parse('LOAD JSONL FROM "var/jsonl/atscreat.jsonl" AS card CREATE card;'))
Tree('script', [
  Tree('statement', [
    Tree('load_clause', [
      Token('FORMAT', 'JSONL'),
      Token('ESCAPED_STRING', '"var/jsonl/atscreat.jsonl"'),
      Tree('target_variable', [
        Token('CNAME', 'card')
      ])
    ]),
    Tree('create_clause', [
      Tree('source_variable', [
        Token('CNAME', 'card')
      ])
    ])
  ])
])
>>> pprint(parser.parse('''
...   MATCH {
...     -- match one card
...     name: "Durin's Folk"
...   };
... '''))
Tree('script', [
  Tree('statement', [
    Tree('match_clause', [
      Tree('target_object', [
        Tree('target_full_pair', [
          Token('CNAME', 'name'),
          Tree('target_constant', [
            Token('ESCAPED_STRING', '"Durin\\'s Folk"')
          ])
        ])
      ])
    ])
  ])
])
"""
import json
import re

from lark import Lark, Tree

from meccg import destructuring, sat

parser = Lark(
    """
    script: (statement ";")* [statement]

    statement: read_clause+ [write_clause]
             | write_clause
    
    ?read_clause: load_clause
                | match_clause
                | with_clause

    load_clause: "LOAD" FORMAT "FROM" ESCAPED_STRING "AS" target_expression
    match_clause: "MATCH" target_expression
    with_clause: "WITH" source_expression "AS" target_expression
    
    ?write_clause: create_clause
                 | save_clause

    create_clause: "CREATE" source_expression

    save_clause: "SAVE" FORMAT source_expression "TO" ESCAPED_STRING
    
    ?target_expression: target_object
                      | target_variable
                      | target_constant
                      | target_alias
                      | target_unwind

    target_object: "{" "}"
                 | "{" target_rest_expression "}"
                 | "{" target_pair ("," target_pair)* ["," target_rest_expression] "}"
    ?target_pair: target_shorthand_pair
                | target_full_pair
    target_shorthand_pair: CNAME
    target_full_pair: CNAME ":" target_expression
    target_rest_expression: "..." target_expression
    
    target_variable: CNAME
    
    target_constant: ESCAPED_STRING
    
    target_alias: target_expression "AS" CNAME
    
    target_unwind: target_expression "[" "]"

    ?source_expression: source_variable

    source_variable: CNAME

    FORMAT: "JSONL"
          | "JSON"
          | "TEXT"

    COMMENT: /--.*/

    %import common.ESCAPED_STRING
    %import common.CNAME
    %import common.WS
    %ignore WS
    %ignore COMMENT
    """, start='script', g_regex_flags=re.IGNORECASE
)


def pprint(node, indent='', last=True):
    comma = ',' if not last else ''
    if isinstance(node, Tree):
        print(f'{indent}Tree({repr(node.data)}, [')
        last_i = len(node.children) - 1
        for i, child in enumerate(node.children):
            pprint(child, indent=indent + ' ' * 2, last=(i == last_i))
        print(f'{indent}]){comma}')
    else:
        print(f'{indent}{repr(node)}{comma}')


class Session:
    def __init__(self):
        self._records = []

    def query(self, query_string):
        query_tree = parser.parse(query_string)
        return self._eval(query_tree, None)

    def _eval(self, node, result):
        if node.data == 'script':
            # return the result of the last statement
            for child in node.children:
                result = self._eval(child, result)
            return result
        elif node.data == 'statement':
            # start with a single empty result and then apply each clause
            result = [{}]
            for child in node.children:
                result = self._eval(child, result)
            return result
        elif node.data == 'load_clause':
            file_format, file_path, target_expression = node.children
            return self._load(result, file_format, json.loads(file_path), target_expression)
        elif node.data == 'match_clause':
            target_expression, = node.children
            return self._match(result, target_expression)
        elif node.data == 'with_clause':
            source_expression, target_expression = node.children
            return self._with(result, source_expression, target_expression)
        elif node.data == 'create_clause':
            source_expression, = node.children
            return self._create(result, source_expression)
        elif node.data == 'save_clause':
            file_format, source_expression, file_path = node.children
            return self._save(result, file_format, source_expression, json.loads(file_path))
        elif isinstance(node, Tree):
            raise Exception(f'Node of type {node.data} not supported')
        else:
            raise Exception(f'Node {node} not supported')

    def _load(self, input_result, file_format, file_path, target_expression):
        compiled_target = self._compile_target(target_expression)
        output_result = []

        for context in input_result:
            if file_format == 'JSON':
                with open(file_path) as fp:
                    source_value = json.load(fp)
                    output_result += [
                        sat.cmb(context, match)
                        for match in compiled_target(source_value)
                        if sat.cmp(context, match)
                    ]
            elif file_format == 'JSONL':
                with open(file_path) as fp:
                    for line in fp:
                        source_value = json.loads(line)
                        output_result += [
                            sat.cmb(context, match)
                            for match in compiled_target(source_value)
                            if sat.cmp(context, match)
                        ]
            else:
                raise Exception(f'File format {file_format} not supported')

        return output_result

    def _create(self, input_result, source_expression):
        compiled_source = self._compile_source(source_expression)

        for context in input_result:
            self._records += compiled_source(context)

        return input_result

    def _match(self, input_result, target_expression):
        compiled_target = self._compile_target(target_expression)
        output_result = []

        for context in input_result:
            output_result += [
                sat.cmb(context, match)
                for record in self._records
                for match in compiled_target(record)
                if sat.cmp(context, match)
            ]

        return output_result

    def _with(self, input_result, source_expression, target_expression):
        compiled_source = self._compile_source(source_expression)
        compiled_target = self._compile_target(target_expression)
        output_result = []

        for context in input_result:
            # NOTE: no check compatibility and no combine
            # matches from WITH should hide input variables, so we throw away all the input variables
            output_result += [
                match
                for value in compiled_source(context)
                for match in compiled_target(value)
            ]

        return output_result

    def _save(self, input_result, file_format, source_expression, file_path):
        compiled_source = self._compile_source(source_expression)

        with open(file_path, 'w') as fp:
            for context in input_result:
                if file_format == 'JSONL':
                    for record in compiled_source(context):
                        json.dump(record, fp)
                        fp.write('\n')
                else:
                    raise Exception(f'File format {file_format} not supported')

        return input_result

    def _compile_target(self, expression):
        if expression.data == 'target_object':
            pairs = {
                str(target_pair.children[0]): (
                    self._compile_target(target_pair.children[1]) if target_pair.data == 'target_full_pair'
                    else destructuring.var(str(target_pair.children[0]))
                )
                for target_pair in expression.children
                if target_pair.data in ('target_shorthand_pair', 'target_full_pair')
            }
            rest = next((
                self._compile_target(child.children[0])
                for child in expression.children
                if child.data == 'target_rest_expression'
            ), None)
            return destructuring.obj(pairs, rest)
        elif expression.data == 'target_constant':
            return destructuring.lit(json.loads(expression.children[0]))
        elif expression.data == 'target_alias':
            return destructuring.als(self._compile_target(expression.children[0]), str(expression.children[1]))
        elif expression.data == 'target_variable':
            return destructuring.var(str(expression.children[0]))
        elif expression.data == 'target_unwind':
            return destructuring.unw(self._compile_target(expression.children[0]))
        else:
            raise Exception(f'Node of type {expression.data} not supported')

    def _compile_source(self, expression):
        if expression.data == 'source_variable':
            k = expression.children[0]
            return lambda x: [x[k]]
        else:
            raise Exception(f'Node of type {expression.data} not supported')
