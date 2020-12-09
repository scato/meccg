from functools import reduce

from jinja2 import Environment
from jinja2.nodes import Name, Getattr, Not, Test, If, Compare
from jinja2.visitor import NodeVisitor

from lib.meccg import untemplating


class UntemplateVisitor(NodeVisitor):
    def visit_list(self, nodes):
        return reduce(untemplating.seq, (self.visit(node) for node in nodes))

    def visit_Template(self, node):
        return untemplating.parser(self.visit(node.body))

    def visit_Output(self, node):
        return self.visit(node.nodes)

    def visit_TemplateData(self, node):
        return untemplating.lit(node.data)

    def _node_to_identifier(self, node):
        if isinstance(node, Name):
            return node.name
        elif isinstance(node, Getattr):
            return self._node_to_identifier(node.node) + '.' + node.attr
        else:
            raise Exception(f'Node of type {type(node)} not supported')

    def visit_Name(self, node):
        return untemplating.var(self._node_to_identifier(node))

    def visit_Getattr(self, node):
        return untemplating.var(self._node_to_identifier(node))

    def visit_For(self, node):
        return untemplating.lst(
            self._node_to_identifier(node.iter),
            self._node_to_identifier(node.target),
            self.visit(node.body)
        )

    def _normalize_if_elif_else(self, node):
        if len(node.elif_) == 0:
            return node
        else:
            return If(
                node.test,
                node.body,
                [],
                [
                    self._normalize_if_elif_else(
                        If(
                            node.elif_[0].test,
                            node.elif_[0].body,
                            node.elif_[1:],
                            node.else_
                        )
                    )
                ]
            )

    def _test_to_value(self, node):
        if isinstance(node, Test):
            if node.name == 'none':
                return None
            else:
                raise Exception(f'Test {node.name} not supported')
        elif isinstance(node, Compare):
            if node.ops[0].op == 'eq':
                return node.ops[0].expr.value
            else:
                raise Exception(f'Compare {node.ops[0].op} not supported')
        else:
            raise Exception(f'Node of type {type(node)} not supported')

    def visit_If(self, node):
        node = self._normalize_if_elif_else(node)

        p = self.visit(node.body)
        if len(node.else_) > 0:
            q = self.visit(node.else_)
        else:
            q = untemplating.lit('')
        if isinstance(node.test, Not):
            test = node.test.node
            q, p = p, q
        else:
            test = node.test
        return untemplating.iff(
            self._node_to_identifier(test.node if isinstance(test, Test) else test.expr),
            self._test_to_value(test),
            p,
            q
        )

    def generic_visit(self, node, *args, **kwargs):
        raise Exception(f'Node of type {type(node)} not supported')


def load_template(template_string, name=None, filename=None):
    """
    >>> t = load_template('<html>')
    >>> t('<html>')
    (True, {})
    >>> t = load_template('{{ name }}')
    >>> t('Oin')
    (True, {'name': 'Oin'})
    >>> t = load_template('<h2>{{ name }}</h2>')
    >>> t('<h2>Oin</h2>')
    (True, {'name': 'Oin'})
    >>> t = load_template('<h2>{{ character.name }}</h2>')
    >>> t('<h2>Oin</h2>')
    (True, {'character': {'name': 'Oin'}})
    >>> t = load_template('<body>{% for name in names %}<h2>{{ name }}</h2>{% endfor %}</body>')
    >>> t('<body><h2>Ori</h2><h2>Dori</h2></body>')
    (True, {'names': ['Ori', 'Dori']})
    >>> t = load_template('<body>{% for name in character.names %}<h2>{{ name }}</h2>{% endfor %}</body>')
    >>> t('<body><h2>Ori</h2><h2>Dori</h2></body>')
    (True, {'character': {'names': ['Ori', 'Dori']}})
    >>> t = load_template('<h2>{{ name }}</h2>')
    >>> t('<b>Oin</b>')
    (False, "Expected '<h2>' at 1:0")
    """
    environment = Environment()
    node = environment.parse(template_string, name=name, filename=filename)
    visitor = UntemplateVisitor()
    parser = visitor.visit(node)

    return parser


def untemplate(template_filename, source_filename):
    with open(template_filename) as fp:
        p = load_template(''.join(fp))

    with open(source_filename) as fp:
        success, result = p(''.join(fp))

        if success:
            return result
        else:
            raise Exception(result)
