from itertools import product


def ctx(k, v):
    """
    Creates a context based on a variable reference and a value
    >>> ctx('name', 'Ori')
    {'name': 'Ori'}
    >>> ctx('character.name', 'Ori')
    {'character': {'name': 'Ori'}}
    """
    return ctx(k.split('.')[0], ctx(k.split('.')[1], v)) if '.' in k else {k: v}


def get(k, c):
    """
    Retrieves a value from a context based on a variable reference
    >>> get('name', {'name': 'Ori'})
    'Ori'
    >>> get('character.name', {'character': {'name': 'Ori'}})
    'Ori'
    """
    if '.' in k:
        return get('.'.join(k.split('.')[1:]), c[k.split('.')[0]])
    else:
        return c[k]


def has(k, c):
    """
    Checks if a context defines a value based on a variable reference
    >>> has('name', {'name': 'Ori'})
    True
    >>> has('character.name', {'character': {'name': 'Ori'}})
    True
    >>> has('character.name', {'name': 'Ori'})
    False
    """
    if '.' in k:
        if k.split('.')[0] in c:
            return has('.'.join(k.split('.')[1:]), c[k.split('.')[0]])
        else:
            return False
    else:
        return k in c


def rem(k, c):
    """
    Removes a values from a context based on a variable reference
    >>> rem('name', {'name': 'Ori', 'text': 'Unique.'})
    {'text': 'Unique.'}
    >>> rem('character.name', {'character': {'name': 'Ori', 'text': 'Unique.'}})
    {'character': {'text': 'Unique.'}}
    """
    if '.' in k:
        return {l: rem('.'.join(k.split('.')[1:]), d) if l == k.split('.')[0] else d for l, d in c.items()}
    else:
        return {l: d for l, d in c.items() if l != k}


def upd(k, f, c):
    """
    Updates a values from a context based on a variable reference
    >>> upd('name', lambda v: v.upper(), {'name': 'Ori', 'text': 'Unique.'})
    {'name': 'ORI', 'text': 'Unique.'}
    >>> upd('character.name', lambda v: v.upper(), {'character': {'name': 'Ori', 'text': 'Unique.'}})
    {'character': {'name': 'ORI', 'text': 'Unique.'}}
    """
    if '.' in k:
        return {l: upd('.'.join(k.split('.')[1:]), f, d) if l == k.split('.')[0] else d for l, d in c.items()}
    else:
        return {l: f(v) if l == k else v for l, v in c.items()}


def cmb(v, w):
    """
    Combines two contexts into one, merging dictionaries and constraints, choosing values over constraints,
    and keeping the second argument if two values are given
    >>> cmb({}, {'name': 'Ori'})
    {'name': 'Ori'}
    >>> cmb({'name': lambda x: x != 'Dori'}, {'name': 'Ori'})
    {'name': 'Ori'}
    >>> cmb({'name': 'Ori'}, {'MP': '1'})
    {'MP': '1', 'name': 'Ori'}
    >>> cmb({'character': {'name': 'Ori'}}, {'character': {'MP': '1'}})
    {'character': {'MP': '1', 'name': 'Ori'}}
    >>> c = cmb({'name': lambda x: x != 'Dori'}, {'name': lambda x: x != 'Ori'})
    >>> c['name']('Ori')
    False
    >>> c['name']('Dori')
    False
    >>> c['name']('Oin')
    True
    >>> cmb({'name': 'Dori'}, {'name': 'Ori'})
    {'name': 'Ori'}
    """
    if isinstance(v, dict) and isinstance(w, dict):
        return {
            k: v[k] if k not in w else w[k] if k not in v else cmb(v.get(k), w.get(k))
            for k in sorted(v.keys() | w.keys())
        }
    elif callable(v) and callable(w):
        return lambda x: v(x) and w(x)
    elif callable(v):
        return w
    elif callable(w):
        return v
    else:
        return w


def cmp(v, w):
    """
    Checks if two contexts are compatible
    >>> cmp({}, {'name': 'Ori'})
    True
    >>> cmp({'name': 'Ori'}, {'name': lambda x: x != 'Dori'})
    True
    >>> cmp({'name': 'Ori'}, {'name': 'Dori'})
    False
    >>> cmp({'name': 'Ori'}, {'name': lambda x: x != 'Ori'})
    False
    >>> cmp({'character': {'name': 'Ori'}}, {'character': {'MP': '1'}})
    True
    >>> cmp({'character': {'name': 'Ori'}}, {'character': {'name': 'Dori'}})
    False
    >>> cmp({'name': lambda x: x == 'Dori'}, {'name': lambda x: x != 'Ori'})
    True
    """
    if callable(v) and callable(w):
        return True
    elif callable(v):
        return v(w)
    elif callable(w):
        return w(v)
    elif isinstance(v, dict) and isinstance(w, dict):
        return all(
            cmp(v.get(k), w.get(k))
            for k in v.keys() & w.keys()
        )
    else:
        return v == w


def var(k):
    """
    Constraint for a boolean variable
    >>> var('x')(True)
    [{'x': True}]
    >>> var('x')(False)
    [{'x': False}]
    """
    return lambda s: [ctx(k, s)]


def eq(k, v):
    """
    An equals contraint
    >>> eq('x', 'Ori')(True)
    [{'x': 'Ori'}]
    >>> eq('x', 'foo')(False)  # doctest: +ELLIPSIS
    [{'x': <function ...>}]
    """
    return lambda s: [ctx(k, v if s else lambda x: x != v)]


def neg(p):
    """
    Negation of a proposition
    >>> neg(var('x'))(True)
    [{'x': False}]
    >>> neg(var('x'))(False)
    [{'x': True}]
    """
    return lambda s: p(not s)


def con(p, q):
    """
    Conjuction (AND) of two propositions
    >>> list(con(var('x'), var('y'))(True))
    [{'x': True, 'y': True}]
    >>> list(con(var('x'), var('y'))(False))
    [{'x': True, 'y': False}, {'x': False, 'y': True}, {'x': False, 'y': False}]
    >>> list(con(var('x'), var('x'))(False))
    [{'x': False}]
    >>> list(con(con(var('x'), var('y')), var('z'))(True))
    [{'x': True, 'y': True, 'z': True}]
    >>> list(con(con(var('x'), var('y')), var('z'))(False))  # doctest: +ELLIPSIS
    [{'x': True, 'y': True, 'z': False}, ..., {'x': False, 'y': False, 'z': False}]
    >>> len(list(con(con(var('x'), var('y')), var('z'))(False)))
    7
    """
    return lambda s: (
        cmb(v, w)
        for t, u in [
            (t, u)
            for t in [True, False]
            for u in [True, False]
            if (t and u) == s
        ]
        for v, w in product(p(t), q(u))
        if cmp(v, w)
    )


def dis(p, q):
    """
    Disjuction (OR) of two propositions
    >>> list(dis(var('x'), var('y'))(True))
    [{'x': True, 'y': True}, {'x': True, 'y': False}, {'x': False, 'y': True}]
    >>> list(dis(var('x'), var('y'))(False))
    [{'x': False, 'y': False}]
    >>> list(dis(var('x'), var('x'))(True))
    [{'x': True}]
    >>> list(dis(dis(var('x'), var('y')), var('z'))(True))  # doctest: +ELLIPSIS
    [{'x': True, 'y': True, 'z': True}, ..., {'x': False, 'y': False, 'z': True}]
    >>> len(list(dis(dis(var('x'), var('y')), var('z'))(True)))
    7
    >>> list(dis(dis(var('x'), var('y')), var('z'))(False))
    [{'x': False, 'y': False, 'z': False}]
    """
    return lambda s: (
        cmb(v, w)
        for t, u in [
            (t, u)
            for t in [True, False]
            for u in [True, False]
            if (t or u) == s
        ]
        for v, w in product(p(t), q(u))
        if cmp(v, w)
    )
