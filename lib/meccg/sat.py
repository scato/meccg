def ctx(k, v):
    """
    Creates a context based on a variable reference and a value
    >>> ctx('name', 'Ori')
    {'name': 'Ori'}
    >>> ctx('character.name', 'Ori')
    {'character': {'name': 'Ori'}}
    """
    return ctx(k.split('.')[0], ctx(k.split('.')[1], v)) if '.' in k else {k: v}


def cmb(v, w):
    """
    Combines two contexts into one
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
    """
    if isinstance(v, dict) and isinstance(w, dict):
        return {
            k: cmb(v.get(k), w.get(k))
            for k in sorted(v.keys() | w.keys())
        }
    elif callable(v) and callable(w):
        return lambda x: v(x) and w(x)
    elif v is None:
        return w
    elif w is None:
        return v
    elif callable(v):
        return w
    elif callable(w):
        return v
    else:
        return v


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
    """
    if callable(v):
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
    """
    return lambda s: (
        cmb(v, w)
        for t, u in [
            (t, u)
            for t in [True, False]
            for u in [True, False]
            if (t and u) == s
        ]
        for v, w in zip(p(t), q(u))
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
    """
    return lambda s: (
        cmb(v, w)
        for t, u in [
            (t, u)
            for t in [True, False]
            for u in [True, False]
            if (t or u) == s
        ]
        for v, w in zip(p(t), q(u))
        if cmp(v, w)
    )
