import glob
import json
import re

import jsonschema
from lark import Lark, Tree, Token

from meccg import destructuring, sat, expr

parser = Lark(r"""
    script: (statement ";")* [statement]

    ?statement: union_statement
              | create_index_statement
    
    create_index_statement: "CREATE" "INDEX" CNAME "ON" target_expression

    ?union_statement: query_statement
                    | union_statement "UNION" query_statement -> union_statement

    query_statement: read_clause+ [write_clause]
                   | write_clause

    subquery: read_clause+
    
    ?read_clause: load_clause
                | match_clause
                | with_clause
                | set_clause
                | where_clause

    load_clause: "LOAD" FORMAT "FROM" target_expression "AS" target_expression
    match_clause: "MATCH" target_expression
    with_clause: "WITH" source_expression "AS" target_expression
    set_clause: "SET" target_variable "=" source_expression
              | "SET" target_global "=" source_expression
    where_clause: "WHERE" source_expression
    
    ?write_clause: create_clause
                 | return_clause
                 | merge_clause
                 | delete_clause
                 | save_clause

    create_clause: "CREATE" source_expression

    return_clause: "RETURN" source_expression
    
    merge_clause: "MERGE" source_expression "INTO" target_expression

    delete_clause: "DELETE" target_expression

    save_clause: "SAVE" FORMAT source_expression "TO" ESCAPED_STRING
    
    ?target_expression: target_constant
                      | target_template
                      | target_variable
                      | target_object
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
                   | target_variable "." CNAME

    target_global: GLOBAL
    
    target_constant: ESCAPED_STRING
                   | /null/
    
    target_template: /`[^`$]*`/
                   | /`[^`$]*\${/ target_expression (/}[^`$]*\${/ target_expression)* /}[^`$]*`/

    target_alias: target_expression "AS" CNAME
    
    target_unwind: target_expression "[" "]"

    ?source_expression: and_expression
    
    ?and_expression: or_expression
                   | and_expression "AND" or_expression -> source_and

    ?or_expression: compare_expression
                  | or_expression "OR" compare_expression -> source_or
    
    ?compare_expression: prefix_expression
                       | compare_expression "==" prefix_expression -> source_eq
                       | compare_expression "!=" prefix_expression -> source_ne
                       | compare_expression "IS" FORMAT "(" source_expression ")" -> source_valid
                       | compare_expression "IS" "NOT" FORMAT "(" source_expression ")" -> source_invalid

    ?prefix_expression: member_expression
                      | "NOT" prefix_expression -> source_not

    ?member_expression: terminal_expression
                      | "EXISTS" "(" subquery ")" -> source_exists
                      | member_expression "." CNAME source_method_arguments -> source_method_call
                      | member_expression "." CNAME -> source_property

    source_method_arguments: "(" ")"
                           | "(" source_expression ("," source_expression)* ")"

    ?terminal_expression: source_constant
                        | source_variable
                        | source_global
                        | source_star
                        | source_object
                        | source_array

    source_constant: ESCAPED_STRING
                   | /null/
    
    source_variable: CNAME

    source_global: GLOBAL

    source_star: "*"

    source_object: "{" "}"
                 | "{" source_object_part ("," source_object_part)* "}"
    ?source_object_part: source_shorthand_pair
                       | source_full_pair
                       | source_spread_expression
    source_shorthand_pair: CNAME
    source_full_pair: CNAME ":" source_expression

    source_array: "[" "]"
                | "[" source_array_part ("," source_array_part)* "]"
    ?source_array_part: source_array_element
                      | source_spread_expression
    source_array_element: source_expression

    source_spread_expression: "..." source_expression

    GLOBAL: "@"? ("_"|LETTER) ("_"|LETTER|DIGIT)*

    FORMAT: "JSONL"
          | "JSON"
          | "TEXT"

    COMMENT: /--.*/

    %import common.ESCAPED_STRING
    %import common.CNAME
    %import common.LETTER
    %import common.DIGIT
    %import common.WS
    %ignore WS
    %ignore COMMENT
""", start='script', g_regex_flags=re.IGNORECASE)


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
        self._globals = {}
        self._index_keys = {}
        self._index_records = {}

    def query(self, query_string):
        query_tree = parser.parse(query_string)
        return self._eval(query_tree, None)

    def _eval(self, node, result):
        if node.data == 'script':
            # start each statement with a single empty result and return the result of the last statement
            for child in node.children:
                result = self._eval(child, [{}])
            return result
        elif node.data == 'query_statement':
            for child in node.children:
                result = self._eval(child, result)
            return result
        elif node.data == 'union_statement':
            left, right = node.children
            left_result = self._eval(left, result)
            right_result = self._eval(right, result)
            return left_result + right_result
        elif node.data == 'subquery':
            # start with the context result and then apply each clause
            for child in node.children:
                result = self._eval(child, result)
            return result
        elif node.data == 'load_clause':
            file_format, file_path, target_expression = node.children
            return self._load(result, file_format, file_path, target_expression)
        elif node.data == 'match_clause':
            target_expression, = node.children
            return self._match(result, target_expression)
        elif node.data == 'with_clause':
            source_expression, target_expression = node.children
            return self._with(result, source_expression, target_expression)
        elif node.data == 'set_clause':
            target_expression, source_expression = node.children
            return self._set(result, target_expression, source_expression)
        elif node.data == 'where_clause':
            source_expression, = node.children
            return self._where(result, source_expression)
        elif node.data == 'create_clause':
            source_expression, = node.children
            return self._create(result, source_expression)
        elif node.data == 'return_clause':
            source_expression, = node.children
            return self._return(result, source_expression)
        elif node.data == 'merge_clause':
            source_expression, target_expression = node.children
            return self._merge(result, source_expression, target_expression)
        elif node.data == 'delete_clause':
            target_expression, = node.children
            return self._delete(result, target_expression)
        elif node.data == 'save_clause':
            file_format, source_expression, file_path = node.children
            return self._save(result, file_format, source_expression, json.loads(file_path))
        elif node.data == 'create_index_statement':
            name, target_expression = node.children
            return self._create_index(name, target_expression)
        elif isinstance(node, Tree):
            raise Exception(f'Node of type {node.data} not supported')
        else:
            raise Exception(f'Node {node} not supported')

    def _load(self, input_result, file_format, file_path, target_expression):
        if file_path.data == 'target_constant':
            file_list = [json.loads(file_path.children[0])]
        elif file_path.data == 'target_template':
            if isinstance(file_path.children[0], str):
                prefix = re.sub(r'^`|^}|`$|\${$', '', file_path.children[0])
            else:
                prefix = ''
            file_list = glob.glob(prefix + '*')
        else:
            raise Exception(f'Loading from node of type {file_path.data} not supported')

        compiled_path = self._compile_target(file_path)
        compiled_target = self._compile_target(target_expression)
        output_result = []

        for context in input_result:
            for file in file_list:
                for match in compiled_path(file.replace('\\', '/')):
                    if sat.cmp(context, match):
                        subcontext = sat.cmb(context, match)
                        with open(file) as fp:
                            if file_format == 'JSON':
                                source_value = json.load(fp)
                                output_result += [
                                    sat.cmb(subcontext, match)
                                    for match in compiled_target(source_value)
                                    if sat.cmp(subcontext, match)
                                ]
                            elif file_format == 'JSONL':
                                for line in fp:
                                    source_value = json.loads(line)
                                    output_result += [
                                        sat.cmb(subcontext, match)
                                        for match in compiled_target(source_value)
                                        if sat.cmp(subcontext, match)
                                    ]
                            else:
                                raise Exception(f'File format {file_format} not supported')

        return output_result

    def _create(self, input_result, source_expression):
        compiled_source = self._compile_source(source_expression)

        for context in input_result:
            self._records.append(compiled_source(context))

        self._update_indexes()
        return input_result

    def _return(self, input_result, source_expression):
        compiled_source = self._compile_source(source_expression)
        output_result = []

        for context in input_result:
            output_result.append(compiled_source(context))

        return output_result

    def _merge(self, input_result, source_expression, target_expression):
        compiled_source = self._compile_source(source_expression)
        compiled_target = self._compile_target(target_expression)

        for context in input_result:
            patch = compiled_source(context)
            for i, record in enumerate(self._records):
                if any(sat.cmp(context, match) for match in compiled_target(record)):
                    self._records[i] = sat.cmb(record, patch)

        self._update_indexes()
        return input_result

    def _delete(self, input_result, target_expression):
        compiled_target = self._compile_target(target_expression)
        delete_set = set()

        for context in input_result:
            for i, record in enumerate(self._records):
                if any(sat.cmp(context, match) for match in compiled_target(record)):
                    delete_set |= {i}

        self._records = [
            record
            for i, record in enumerate(self._records)
            if i not in delete_set
        ]

        self._update_indexes()
        return input_result

    def _match(self, input_result, target_expression):
        compiled_target = self._compile_target(target_expression)
        output_result = []

        for context in input_result:
            simplified_target = self._simplify_target(target_expression, context)
            index_name = None
            lookup_key = None
            for name, key_expression in self._index_keys.items():
                lookup_key = self._calc_lookup_key(simplified_target, key_expression)
                if lookup_key is not None:
                    index_name = name
                    break

            if lookup_key is not None:
                record_key = json.dumps(lookup_key)
                candidate_records = (
                    self._records[i]
                    for i in self._index_records[index_name][record_key]
                )
            else:
                candidate_records = self._records

            output_result += [
                sat.cmb(context, match)
                for record in candidate_records
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
                for match in compiled_target(compiled_source(context))
            ]

        return output_result

    def _set(self, input_result, target_expression, source_expression):
        if target_expression.data == 'target_global':
            compiled_source = self._compile_source(source_expression)

            for context in input_result:
                key = str(target_expression.children[0])
                value = compiled_source(context)
                self._globals[key] = value

            return input_result
        else:
            compiled_target = self._compile_target(target_expression)
            compiled_source = self._compile_source(source_expression)
            output_result = []

            for context in input_result:
                # NOTE: no check compatibility but combine to make sure we keep the new value
                output_result += [
                    sat.cmb(context, match)
                    for match in compiled_target(compiled_source(context))
                ]

            return output_result

    def _where(self, input_result, source_expression):
        compiled_source = self._compile_source(source_expression)
        output_result = []

        for context in input_result:
            if compiled_source(context):
                output_result.append(context)

        return output_result

    def _save(self, input_result, file_format, source_expression, file_path):
        compiled_source = self._compile_source(source_expression)

        with open(file_path, 'w') as fp:
            for context in input_result:
                if file_format == 'JSONL':
                    json.dump(compiled_source(context), fp)
                    fp.write('\n')
                else:
                    raise Exception(f'File format {file_format} not supported')

        return input_result

    def _create_index(self, name, key_expression):
        self._index_keys[name] = key_expression

        self._update_indexes()
        return None

    def _update_indexes(self):
        for name, key_expression in self._index_keys.items():
            compiled_key = self._compile_target(key_expression)
            self._index_records[name] = {}
            for i, record in enumerate(self._records):
                for match in compiled_key(record):
                    record_key = json.dumps(match)
                    if record_key not in self._index_records[name]:
                        self._index_records[name][record_key] = set()
                    self._index_records[name][record_key] |= {i}

    def _compile_identifier(self, expression):
        if isinstance(expression, Token):
            return str(expression)
        elif expression.data == 'target_variable':
            return '.'.join(
                self._compile_identifier(child)
                for child in expression.children
            )
        else:
            raise Exception(f'Node of type {expression.data} not supported')

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
            key = self._compile_identifier(expression)
            return destructuring.var(key)
        elif expression.data == 'target_unwind':
            return destructuring.unw(self._compile_target(expression.children[0]))
        elif expression.data == 'target_template':
            return destructuring.tpl([
                re.sub(r'^`|^}|`$|\${$', '', child) if isinstance(child, str) else self._compile_target(child)
                for child in expression.children
            ])
        else:
            raise Exception(f'Node of type {expression.data} not supported')

    def _compile_source(self, expression):
        if expression.data == 'source_method_call':
            subject = self._compile_source(expression.children[0])
            arguments = self._compile_source(expression.children[2])
            if expression.children[1] == 'replace':
                return expr.bin(lambda o, a: o.replace(*a), subject, arguments)
            elif expression.children[1] == 'split':
                return expr.bin(lambda o, a: [o] if a == [] else list(o) if a == [''] else o.split(*a), subject, arguments)
            elif expression.children[1] == 'join':
                return expr.bin(lambda o, a: (a[0] if len(a) > 0 else ',').join(o), subject, arguments)
            elif expression.children[1] == 'includes':
                return expr.bin(lambda o, a: a[0] in o, subject, arguments)
            else:
                raise Exception(f'Method {expression.children[1]} not supported')
        elif expression.data == 'source_property':
            left = self._compile_source(expression.children[0])
            key = str(expression.children[1])
            return expr.uni(lambda l: l[key], left)
        elif expression.data == 'source_ne':
            left = self._compile_source(expression.children[0])
            right = self._compile_source(expression.children[1])
            return expr.bin(lambda l, r: l != r, left, right)
        elif expression.data == 'source_and':
            left = self._compile_source(expression.children[0])
            right = self._compile_source(expression.children[1])
            return expr.bin(lambda l, r: l and r, left, right)
        elif expression.data == 'source_valid':
            left = self._compile_source(expression.children[0])
            format = str(expression.children[1])
            right = self._compile_source(expression.children[2])
            return expr.bin(lambda l, r: self._validate(format, l, r), left, right)
        elif expression.data == 'source_invalid':
            left = self._compile_source(expression.children[0])
            format = str(expression.children[1])
            right = self._compile_source(expression.children[2])
            return expr.bin(lambda l, r: not self._validate(format, l, r), left, right)
        elif expression.data == 'source_not':
            operand = self._compile_source(expression.children[0])
            return expr.uni(lambda o: not o, operand)
        elif expression.data == 'source_method_arguments':
            return expr.arr([
                expr.el(self._compile_source(child))
                for child in expression.children
            ])
        elif expression.data == 'source_constant':
            return expr.lit(json.loads(expression.children[0]))
        elif expression.data == 'source_variable':
            k = str(expression.children[0])
            return expr.var(k)
        elif expression.data == 'source_global':
            k = str(expression.children[0])
            return lambda c: self._globals[k]
        elif expression.data == 'source_star':
            return expr.star()
        elif expression.data == 'source_object':
            elements = [self._compile_source(child) for child in expression.children]
            return expr.obj(elements)
        elif expression.data == 'source_shorthand_pair':
            k = str(expression.children[0])
            v = expr.var(k)
            return expr.kvp(k, v)
        elif expression.data == 'source_full_pair':
            k = str(expression.children[0])
            v = self._compile_source(expression.children[1])
            return expr.kvp(k, v)
        elif expression.data == 'source_array':
            elements = [self._compile_source(child) for child in expression.children]
            return expr.arr(elements)
        elif expression.data == 'source_array_element':
            return expr.el(self._compile_source(expression.children[0]))
        elif expression.data == 'source_spread_expression':
            return self._compile_source(expression.children[0])
        elif expression.data == 'source_exists':
            subquery = expression.children[0]
            return lambda c: len(self._eval(subquery, [c])) > 0
        else:
            raise Exception(f'Node of type {expression.data} not supported')

    def _validate(self, format, instance, schema):
        if format == 'JSON':
            try:
                jsonschema.validate(instance, schema)
            except jsonschema.ValidationError:
                return False
            return True
        else:
            raise Exception(f'Validating format {format} is not supported')

    def _simplify_target(self, expression, context):
        if expression.data == 'target_object':
            pairs = [
                (
                    Tree('target_full_pair', [
                        target_pair.children[0],
                        self._simplify_target(target_pair.children[1], context)
                    ]) if target_pair.data == 'target_full_pair'
                    else Tree('target_full_pair', [
                        target_pair.children[0],
                        self._simplify_target(Tree('target_variable', target_pair.children), context)
                    ])
                )
                for target_pair in expression.children
                if target_pair.data in ('target_shorthand_pair', 'target_full_pair')
            ]
            rest = next((
                self._simplify_target(child.children[0], context)
                for child in expression.children
                if child.data == 'target_rest_expression'
            ), None)
            children = pairs
            if rest is not None:
                children.append(rest)
            return Tree('target_object', children)
        elif expression.data == 'target_variable':
            key = self._compile_identifier(expression)
            if sat.has(key, context):
                return Tree('target_constant', [json.dumps(sat.get(key, context))])
            else:
                return expression
        else:
            return expression

    def _calc_lookup_key(self, target_expression, key_expression):
        if target_expression.data == 'target_object' and key_expression.data == 'target_object':
            pairs = {
                str(target_pair.children[0]): (
                    target_pair.children[1] if target_pair.data == 'target_full_pair'
                    else Tree('target_variable', target_pair.children)
                )
                for target_pair in target_expression.children
                if target_pair.data in ('target_shorthand_pair', 'target_full_pair')
            }
            rest = next((
                child.children[0]
                for child in target_expression.children
                if child.data == 'target_rest_expression'
            ), None)

            lookup_key = {}
            for child in key_expression.children:
                if child.data == 'target_shorthand_pair':
                    key = str(child.children[0])
                    if key not in pairs:
                        return None
                    elif pairs[key].data != 'target_constant':
                        return None
                    else:
                        lookup_key = sat.cmb(
                            lookup_key,
                            sat.ctx(key, json.loads(pairs[key].children[0]))
                        )
                elif child.data == 'target_full_pair':
                    key = str(child.children[0])
                    if key not in pairs:
                        return None
                    else:
                        lookup_key = sat.cmb(
                            lookup_key,
                            self._calc_lookup_key(pairs[key], child.children[1])
                        )
                elif child.data == 'target_rest_expression':
                    if rest is None:
                        return None

            return lookup_key
        elif target_expression.data == 'target_constant' and key_expression.data == 'target_variable':
            return sat.ctx(str(key_expression.children[0]), json.loads(target_expression.children[0]))
        else:
            return None