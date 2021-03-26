import re

from meccg import sat


def lit(v):
    """
    Match a value against a literal value
    >>> e = lit('foo')
    >>> e('bar')
    []
    >>> e('foo')
    [{}]
    """
    return lambda x: [{}] if x == v else []


def var(k):
    """
    Match a value into a variable k
    >>> e = var('foo')
    >>> e('bar')
    [{'foo': 'bar'}]
    """
    return lambda x: [sat.ctx(k, x)]


def als(e, k):
    """
    Destructure a value using expression e, assigning te original value to alias k
    >>> e = als(lit('foo'), 'foo')
    >>> e('bar')
    []
    >>> e('foo')
    [{'foo': 'foo'}]
    """
    return lambda x: [
        sat.cmb(c, d)
        for c in e(x)
        for d in [sat.ctx(k, x)]
        if sat.cmp(c, d)
    ]


def obj(p, r=None):
    """
    Destructure an Python dictionary (like a JS object)
    >>> e = obj({})
    >>> e('foo')
    []
    >>> e({})
    [{}]
    >>> e = obj({'type': lit('Character')})
    >>> e({})
    []
    >>> e({'type': 'Hazard'})
    []
    >>> e = obj({'type': lit('Character')}, var('card'))
    >>> e({'type': 'Character', 'name': 'Beorn'})
    [{'card': {'name': 'Beorn'}}]
    """
    def match(x):
        if isinstance(x, dict):
            result = [{}]
            for n, e in p.items():
                if n in x:
                    result = [
                        sat.cmb(c, d)
                        for c in result
                        for d in e(x[n])
                        if sat.cmp(c, d)
                    ]
                else:
                    return []
            if r is not None:
                y = {k: v for k, v in x.items() if k not in p}
                result = [
                    sat.cmb(c, d)
                    for c in result
                    for d in r(y)
                    if sat.cmp(c, d)
                ]
            return result
        else:
            return []

    return match


def tup(es):
    """
    Destructure a Python list (like JS tuple destructuring)
    >>> e = tup([var('a'), var('b')])
    >>> e([1])
    []
    >>> e([1, 2])
    [{'a': 1, 'b': 2}]
    """
    def match(x):
        if isinstance(x, list):
            result = [{}]
            for i, e in enumerate(es):
                if len(x) > i:
                    result = [
                        sat.cmb(c, d)
                        for c in result
                        for d in e(x[i])
                        if sat.cmp(c, d)
                    ]
                else:
                    return []
            return result
        else:
            return []

    return match


def unw(e):
    """
    Unwind an array, matching each element using expression e
    >>> e = unw(var('x'))
    >>> e([1, 2])
    [{'x': 1}, {'x': 2}]
    """
    def match(x):
        if isinstance(x, list):
            return [z for y in x for z in e(y)]
        else:
            return []

    return match


def tpl(ps):
    """
    Match a string against a template
    >>> e = tpl(['var/jsonl/', var('source'), '.jsonl'])
    >>> e('var/json/atscreat.json')
    []
    >>> e('var/jsonl/atscreat.jsonl')
    [{'source': 'atscreat'}]
    """
    pattern = ''.join(
        re.escape(p) if isinstance(p, str) else '(.*)'
        for p in ps
    )

    capture = tup([p for p in ps if not isinstance(p, str)])

    def match(x):
        if isinstance(x, str):
            result = re.match(pattern, x)
            if result is None:
                return []
            else:
                return capture(list(result.groups()))
        else:
            return []

    return match
