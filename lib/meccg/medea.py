import glob
import itertools
import json
import re

import jsonschema
from lark import Lark, Tree, Token

from meccg import destructuring, sat, expr

parser = Lark(r"""
    script: (statement ";")*

    ?statement: union_statement
              | create_index_statement
              | drop_index_statement
    
    create_index_statement: "CREATE" "INDEX" CNAME "ON" target_expression

    drop_index_statement: "DROP" "INDEX" CNAME

    ?union_statement: query_statement
                    | union_statement "UNION" query_statement -> union_statement

    query_statement: read_clause+ [write_clause]
                   | write_clause

    subquery: read_clause+ [return_clause]
    
    ?read_clause: load_clause
                | match_clause
                | with_clause
                | set_clause
                | where_clause
                | order_by_clause

    load_clause: "LOAD" FORMAT "FROM" target_expression "AS" target_expression
    match_clause: "MATCH" target_expression
    with_clause: "WITH" with_pair ("," with_pair)*
    set_clause: "SET" target_variable "=" source_expression
              | "SET" target_global "=" source_expression
    where_clause: "WHERE" source_expression
    order_by_clause: "ORDER" "BY" source_expression

    ?with_pair: with_shorthand_pair
              | with_full_pair
    with_shorthand_pair: source_variable | source_star
    with_full_pair: source_expression "AS" target_expression
    
    ?write_clause: create_clause
                 | return_clause
                 | merge_clause
                 | delete_clause
                 | save_clause

    create_clause: "CREATE" source_expression

    return_clause: "RETURN" source_expression
                 | "RETURN" "DISTINCT" source_expression -> return_distinct_clause
    
    merge_clause: "MERGE" source_expression "INTO" target_expression

    delete_clause: "DELETE" target_expression

    save_clause: "SAVE" FORMAT source_expression "TO" source_expression
    
    ?target_expression: target_constant
                      | target_template
                      | target_variable
                      | target_object
                      | target_tuple
                      | target_alias
                      | target_unwind
                      | target_unpack

    target_object: "{" "}"
                 | "{" target_rest_expression "}"
                 | "{" target_pair ("," target_pair)* ["," target_rest_expression] "}"
    ?target_pair: target_shorthand_pair
                | target_full_pair
    target_shorthand_pair: CNAME ["=" target_constant]
    target_full_pair: CNAME ":" target_expression ["=" target_constant]
    
    target_tuple: "[" "]"
                | "[" target_rest_expression "]"
                | "[" target_element ("," target_element)* ["," target_rest_expression] "]"
    target_element: target_expression
    
    target_rest_expression: "..." target_expression
    
    target_variable: CNAME
                   | target_variable "." CNAME

    target_global: GLOBAL
    
    target_constant: ESCAPED_STRING
                   | SIGNED_NUMBER
                   | /null/
                   | /\[\]/
    
    target_template: /`[^`$]*`/
                   | /`[^`$]*\${/ target_expression (/}[^`$]*\${/ target_expression)* /}[^`$]*`/

    target_alias: target_expression "AS" CNAME
    
    target_unwind: target_expression "[" "]"

    target_unpack: "{" "[" target_expression "]" ":" target_expression "}"

    ?source_expression: and_expression
    
    ?and_expression: or_expression
                   | and_expression "AND" or_expression -> source_and

    ?or_expression: compare_expression
                  | or_expression "OR" compare_expression -> source_or
    
    ?compare_expression: add_expression
                       | compare_expression "==" prefix_expression -> source_eq
                       | compare_expression "!=" prefix_expression -> source_ne
                       | compare_expression "IS" FORMAT "(" source_expression ")" -> source_valid
                       | compare_expression "IS" "NOT" FORMAT "(" source_expression ")" -> source_invalid

    ?add_expression: prefix_expression
                   | add_expression "+" prefix_expression -> source_add

    ?prefix_expression: member_expression
                      | "NOT" prefix_expression -> source_not

    ?member_expression: terminal_expression
                      | case_expression
                      | "EXISTS" "(" subquery ")" -> source_subquery_exists
                      | "ARRAY" "(" subquery ")" -> source_subquery_array
                      | member_expression "." CNAME source_method_arguments -> source_method_call
                      | member_expression "." CNAME -> source_property
                      | member_expression "[" "]" -> source_aggregate
                      | member_expression "[" source_expression "]" -> source_element

    case_expression: "CASE" case_expression_case* case_expression_else? "END" -> source_boolean_case
                   | "CASE" source_expression case_expression_case* case_expression_else? "END" -> source_match_case

    case_expression_case: "WHEN" source_expression "THEN" source_expression -> source_boolean_when
    case_expression_else: "ELSE" source_expression -> source_boolean_else

    source_method_arguments: "(" ")"
                           | "(" source_expression ("," source_expression)* ")"

    ?terminal_expression: source_constant
                        | source_variable
                        | source_global
                        | source_star
                        | source_object
                        | source_array
                        | source_template
                        | "(" source_expression ")"

    source_constant: ESCAPED_STRING
                   | SIGNED_NUMBER
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
    
    source_template: /`[^`$]*`/
                   | /`[^`$]*\${/ source_expression (/}[^`$]*\${/ source_expression)* /}[^`$]*`/

    GLOBAL: "@"? ("_"|LETTER) ("_"|LETTER|DIGIT)*

    FORMAT: "JSONL"
          | "JSON"
          | "TEXT"

    INLINE_COMMENT: /--.*/
    MULTILINE_COMMENT: "/*" /(.|\n|\r)*?/ "*/"

    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
    %import common.CNAME
    %import common.LETTER
    %import common.DIGIT
    %import common.WS
    %ignore WS
    %ignore INLINE_COMMENT
    %ignore MULTILINE_COMMENT
""", start='script', g_regex_flags=re.IGNORECASE)


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
            if left_result is None:
                return right_result
            elif right_result is None:
                return left_result
            else:
                return itertools.chain(left_result, right_result)
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
            return self._with(result, node)
        elif node.data == 'set_clause':
            target_expression, source_expression = node.children
            return self._set(result, target_expression, source_expression)
        elif node.data == 'where_clause':
            source_expression, = node.children
            return self._where(result, source_expression)
        elif node.data == 'order_by_clause':
            source_expression, = node.children
            return self._order_by(result, source_expression)
        elif node.data == 'create_clause':
            source_expression, = node.children
            return self._create(result, source_expression)
        elif node.data == 'return_clause':
            source_expression, = node.children
            return self._return(result, False, source_expression)
        elif node.data == 'return_distinct_clause':
            source_expression, = node.children
            return self._return(result, True, source_expression)
        elif node.data == 'merge_clause':
            source_expression, target_expression = node.children
            return self._merge(result, source_expression, target_expression)
        elif node.data == 'delete_clause':
            target_expression, = node.children
            return self._delete(result, target_expression)
        elif node.data == 'save_clause':
            file_format, source_expression, file_path = node.children
            return self._save(result, file_format, source_expression, file_path)
        elif node.data == 'create_index_statement':
            name, target_expression = node.children
            return self._create_index(name, target_expression)
        elif node.data == 'drop_index_statement':
            name, = node.children
            return self._drop_index(name)
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

        for context in input_result:
            for file in file_list:
                for match in compiled_path(file.replace('\\', '/')):
                    if sat.cmp(context, match):
                        subcontext = sat.cmb(context, match)
                        with open(file, encoding='UTF-8') as fp:
                            if file_format == 'JSON':
                                source_value = json.load(fp)
                                yield from (
                                    sat.cmb(subcontext, match)
                                    for match in compiled_target(source_value)
                                    if sat.cmp(subcontext, match)
                                )
                            elif file_format == 'JSONL':
                                for line in fp:
                                    source_value = json.loads(line)
                                    yield from (
                                        sat.cmb(subcontext, match)
                                        for match in compiled_target(source_value)
                                        if sat.cmp(subcontext, match)
                                    )
                            elif file_format == 'TEXT':
                                for line in fp:
                                    source_value = line[:-1] if line.endswith('\n') else line
                                    yield from (
                                        sat.cmb(subcontext, match)
                                        for match in compiled_target(source_value)
                                        if sat.cmp(subcontext, match)
                                    )
                            else:
                                raise Exception(f'File format {file_format} not supported')

    def _create(self, input_result, source_expression):
        compiled_source = self._compile_source(source_expression)

        for context in input_result:
            self._records.append(compiled_source(context))

        self._update_indexes()
        return input_result

    def _return(self, input_result, distinct, source_expression):
        compiled_source = self._compile_source(source_expression)

        if distinct:
            found = set()
            for context in input_result:
                value = compiled_source(context)
                value_json = json.dumps(value)
                if value_json not in found:
                    found.add(value_json)
                    yield value
        else:
            for context in input_result:
                yield compiled_source(context)

    def _merge(self, input_result, source_expression, target_expression):
        compiled_projection, target_expression = self._compile_merge_projection(source_expression, target_expression)
        # compiled_source = self._compile_source(source_expression)
        compiled_target = self._compile_target(target_expression)

        # TODO: first generate changeset so that changes are isolated from reading query???

        for patch, context in compiled_projection(input_result):
            for i, record in self._candidate_records(target_expression, context):
                if any(sat.cmp(context, match) for match in compiled_target(record)):
                    self._records[i] = sat.cmb(record, patch)

        self._update_indexes()
        return None

    def _delete(self, input_result, target_expression):
        compiled_target = self._compile_target(target_expression)
        delete_set = set()

        for context in input_result:
            for i, record in self._candidate_records(target_expression, context):
                if any(sat.cmp(context, match) for match in compiled_target(record)):
                    delete_set |= {i}

        self._records = [
            record
            for i, record in enumerate(self._records)
            if i not in delete_set
        ]

        self._update_indexes()
        return None

    def _candidate_records(self, target_expression, context):
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
            return (
                (i, self._records[i])
                for i in self._index_records[index_name].get(record_key, set())
            )
        else:
            return enumerate(self._records)

    def _match(self, input_result, target_expression):
        compiled_target = self._compile_target(target_expression)

        for context in input_result:
            yield from (
                sat.cmb(context, match)
                for i, record in self._candidate_records(target_expression, context)
                for match in compiled_target(record)
                if sat.cmp(context, match)
            )

    def _with(self, input_result, with_clause):
        compiled_projection = self._compile_projection(with_clause)
        compiled_target = self._compile_target(with_clause)

        # NOTE: no check compatibility and no combine
        # matches from WITH should hide input variables, so we throw away all the input variables
        for value, context in compiled_projection(input_result):
            for match in compiled_target(value):
                yield match

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

        for context in input_result:
            if compiled_source(context):
                yield context

    def _order_by(self, input_result, source_expression):
        compiled_source = self._compile_source(source_expression)

        return sorted(input_result, key=lambda x: json.dumps(compiled_source(x)))

    def _save(self, input_result, file_format, source_expression, file_path):
        compiled_source = self._compile_source(source_expression)
        compiled_file_path = self._compile_source(file_path)

        for file_path_string, input_result_group in itertools.groupby(input_result, compiled_file_path):
            with open(file_path_string, 'w', encoding='UTF-8') as fp:
                for context in input_result_group:
                    if file_format == 'JSONL':
                        json.dump(compiled_source(context), fp)
                        fp.write('\n')
                    elif file_format == 'TEXT':
                        fp.write(compiled_source(context))
                        fp.write('\n')
                    else:
                        raise Exception(f'File format {file_format} not supported')

        return None

    def _create_index(self, name, key_expression):
        if name in self._index_keys:
            raise Exception(f'Index {name} already exists')

        self._index_keys[name] = key_expression

        self._update_indexes()
        return None

    def _drop_index(self, name):
        del self._index_keys[name]

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
                if isinstance(child, Token) or child.data != 'target_constant'
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
            defaults = {
                str(target_pair.children[0]): (
                    json.loads(target_pair.children[2].children[0]) if target_pair.data == 'target_full_pair'
                    else json.loads(target_pair.children[1].children[0])
                )
                for target_pair in expression.children
                if target_pair.data in ('target_shorthand_pair', 'target_full_pair')
                and len(target_pair.children) == (3 if target_pair.data == 'target_full_pair' else 2)
            }
            rest = next((
                self._compile_target(child.children[0])
                for child in expression.children
                if child.data == 'target_rest_expression'
            ), None)
            return destructuring.obj(pairs, defaults, rest)
        elif expression.data == 'target_tuple':
            elements = [
                self._compile_target(target_element.children[0])
                for target_element in expression.children
                if target_element.data == 'target_element'
            ]
            rest = next((
                self._compile_target(child.children[0])
                for child in expression.children
                if child.data == 'target_rest_expression'
            ), None)
            if rest is not None:
                raise Exception('target_rest_expression in target_tuple not supported')
            return destructuring.tup(elements, rest)
        elif expression.data == 'target_constant':
            return destructuring.lit(json.loads(expression.children[0]))
        elif expression.data == 'target_alias':
            return destructuring.als(self._compile_target(expression.children[0]), str(expression.children[1]))
        elif expression.data == 'target_variable':
            key = self._compile_identifier(expression)
            return destructuring.var(key)
        elif expression.data == 'target_unwind':
            return destructuring.unw(self._compile_target(expression.children[0]))
        elif expression.data == 'target_unpack':
            return destructuring.unp(self._compile_target(expression.children[0]), self._compile_target(expression.children[1]))
        elif expression.data == 'target_template':
            return destructuring.tpl([
                re.sub(r'^`|^}|`$|\${$', '', child) if isinstance(child, str) else self._compile_target(child)
                for child in expression.children
            ])
        elif expression.data == 'with_clause':
            elements = [
                self._compile_target(child)
                for child in expression.children
            ]
            return destructuring.tup(elements)
        elif expression.data == 'with_full_pair':
            return self._compile_target(expression.children[1])
        elif expression.data == 'with_shorthand_pair':
            source_variable = expression.children[0]
            target_variable = Tree('target_variable', source_variable.children)
            return self._compile_target(target_variable)
        elif expression.data == 'target_key':
            return destructuring.key(int(expression.children[0]))
        else:
            raise Exception(f'Node of type {expression.data} not supported')

    def _contains_aggregate(self, expression):
        if expression.data == 'source_variable':
            return False
        elif expression.data == 'source_constant':
            return False
        elif expression.data == 'source_aggregate':
            return True
        elif expression.data == 'source_object':
            return any(self._contains_aggregate(child) for child in expression.children)
        elif expression.data == 'source_full_pair':
            return self._contains_aggregate(expression.children[1])
        elif expression.data == 'source_shorthand_pair':
            return False
        elif expression.data == 'source_spread_expression':
            return self._contains_aggregate(expression.children[0])
        elif expression.data == 'with_clause':
            return any(self._contains_aggregate(child) for child in expression.children)
        elif expression.data == 'with_full_pair':
            return self._contains_aggregate(expression.children[0])
        elif expression.data == 'with_shorthand_pair':
            return self._contains_aggregate(expression.children[0])
        elif expression.data == 'source_element':
            return any(self._contains_aggregate(child) for child in expression.children)
        elif expression.data == 'source_array':
            return any(self._contains_aggregate(child) for child in expression.children)
        elif expression.data == 'source_array_element':
            return any(self._contains_aggregate(child) for child in expression.children)
        elif expression.data == 'source_method_call':
            return any(self._contains_aggregate(child) for child in expression.children if not isinstance(child, Token))
        elif expression.data == 'source_method_arguments':
            return any(self._contains_aggregate(child) for child in expression.children)
        else:
            raise Exception(f'Node of type {expression.data} not supported')

    def _extract_keys(self, expression, keys):
        if expression.data == 'source_aggregate':
            return keys, expression
        elif expression.data in (
                'with_clause', 'source_object', 'source_full_pair', 'source_constant',
                'target_object', 'target_full_pair', 'target_constant',
        ):
            new_children = []
            for child in expression.children:
                if isinstance(child, Token):
                    new_children.append(child)
                else:
                    keys, new_child = self._extract_keys(child, keys)
                    new_children.append(new_child)
            return keys, Tree(expression.data, new_children)
        elif expression.data == 'with_full_pair':
            source_variable = expression.children[0]
            keys, source_variable = self._extract_keys(source_variable, keys)
            return keys, Tree('with_full_pair', [source_variable, expression.children[1]])
        elif expression.data == 'with_shorthand_pair':
            source_variable = expression.children[0]
            target_variable = Tree('target_variable', source_variable.children)
            keys, source_variable = self._extract_keys(source_variable, keys)
            return keys, Tree('with_full_pair', [source_variable, target_variable])
        elif expression.data == 'source_variable':
            return keys + [expression], Tree('source_key', [Token('INT', len(keys))])
        elif expression.data == 'target_shorthand_pair':
            target_key = expression.children[0]
            target_value = Tree('target_variable', [target_key])
            keys, target_value = self._extract_keys(target_value, keys)
            return keys, Tree('target_full_pair', [target_key, target_value])
        elif expression.data == 'target_variable':
            source_variable = Tree('source_variable', expression.children)
            return keys + [source_variable], Tree('target_key', [Token('INT', len(keys))])
        else:
            raise Exception(f'Node of type {expression.data} not supported')

    def _compile_projection(self, expression):
        if self._contains_aggregate(expression):
            keys, grouped_expression = self._extract_keys(expression, [])
            return expr.grp_ret(
                expr.arr([expr.el(self._compile_source(key)) for key in keys]),
                self._compile_source(grouped_expression)
            )
        else:
            return expr.ret(self._compile_source(expression))

    def _compile_merge_projection(self, source_expression, target_expression):
        if self._contains_aggregate(source_expression):
            keys, grouped_target_expression = self._extract_keys(target_expression, [])
            keys, grouped_source_expression = self._extract_keys(source_expression, keys)
            return expr.grp_ret(
                expr.arr([expr.el(self._compile_source(key)) for key in keys]),
                self._compile_source(grouped_source_expression)
            ), grouped_target_expression
        else:
            return expr.ret(self._compile_source(source_expression)), target_expression

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
            elif expression.children[1] == 'trim':
                return expr.bin(lambda o, a: o.strip(), subject, arguments)
            elif expression.children[1] == 'match':
                to_arr_or_null = lambda x: [x[0], *x.groups()] if x is not None else None
                return expr.bin(lambda o, a: to_arr_or_null(re.search(a[0], o)), subject, arguments)
            else:
                raise Exception(f'Method {expression.children[1]} not supported')
        elif expression.data == 'source_property':
            left = self._compile_source(expression.children[0])
            key = str(expression.children[1])
            return expr.uni(lambda l: l[key], left)
        elif expression.data == 'source_element':
            left = self._compile_source(expression.children[0])
            key = self._compile_source(expression.children[1])
            return expr.bin(lambda l, k: l[k], left, key)
        elif expression.data == 'source_eq':
            left = self._compile_source(expression.children[0])
            right = self._compile_source(expression.children[1])
            return expr.bin(lambda l, r: l == r, left, right)
        elif expression.data == 'source_ne':
            left = self._compile_source(expression.children[0])
            right = self._compile_source(expression.children[1])
            return expr.bin(lambda l, r: l != r, left, right)
        elif expression.data == 'source_and':
            left = self._compile_source(expression.children[0])
            right = self._compile_source(expression.children[1])
            # don't use expr.bin(), but build short-circuit AND
            return lambda c: left(c) and right(c)
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
        elif expression.data == 'source_add':
            left = self._compile_source(expression.children[0])
            right = self._compile_source(expression.children[1])
            return expr.bin(lambda l, r: l + r, left, right)
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
        elif expression.data == 'source_aggregate':
            return expr.grp_arr(self._compile_source(expression.children[0]))
        elif expression.data == 'source_subquery_exists':
            subquery = expression.children[0]
            return lambda c: any(True for _ in self._eval(subquery, [c]))
        elif expression.data == 'source_subquery_array':
            subquery = expression.children[0]
            return lambda c: list(self._eval(subquery, [c]))
        elif expression.data == 'with_clause':
            elements = [self._compile_source(child) for child in expression.children]
            return expr.arr(elements)
        elif expression.data == 'with_full_pair':
            return expr.el(self._compile_source(expression.children[0]))
        elif expression.data == 'with_shorthand_pair':
            return expr.el(self._compile_source(expression.children[0]))
        elif expression.data == 'source_key':
            return expr.grp_key(int(expression.children[0]))
        elif expression.data == 'source_boolean_case':
            right = expr.lit(None)
            for child in reversed(expression.children):
                cond = self._compile_source(child.children[0])
                left = self._compile_source(child.children[1])
                right = expr.ter(cond, left, right)

            return right
        elif expression.data == 'source_match_case':
            value = self._compile_source(expression.children[0])
            children = expression.children[1:]
            if children[-1].data == 'source_boolean_else':
                right = self._compile_source(children[-1].children[0])
                children = children[:-1]
            else:
                right = expr.lit(None)
            for child in reversed(children):
                cond = expr.bin(lambda l, r: l == r, value, self._compile_source(child.children[0]))
                left = self._compile_source(child.children[1])
                right = expr.ter(cond, left, right)

            return right
        elif expression.data == 'source_template':
            return expr.tpl([
                re.sub(r'^`|^}|`$|\${$', '', child) if isinstance(child, str) else self._compile_source(child)
                for child in expression.children
            ])
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
        elif expression.data == 'target_key':
            i = int(expression.children[0])
            if '$keys' in context and len(context['$keys']) > i:
                return Tree('target_constant', [json.dumps(context['$keys'][i])])
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
