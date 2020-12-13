import re

import lib.meccg.parsing as parsing


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
    >>> cmb({'name': 'Ori'}, {'MP': '1'})
    {'MP': '1', 'name': 'Ori'}
    >>> cmb({'character': {'name': 'Ori'}}, {'character': {'MP': '1'}})
    {'character': {'MP': '1', 'name': 'Ori'}}
    """
    if isinstance(v, dict) and isinstance(w, dict):
        return {
            k: cmb(v.get(k), w.get(k))
            for k in sorted(v.keys() | w.keys())
        }
    elif v is None:
        return w
    else:
        return v


def cmp(v, w):
    """
    Checks if two contexts are compatible
    >>> cmp({}, {'name': 'Ori'})
    True
    >>> cmp({'name': 'Ori'}, {'name': 'Dori'})
    False
    >>> cmp({'character': {'name': 'Ori'}}, {'character': {'MP': '1'}})
    True
    >>> cmp({'character': {'name': 'Ori'}}, {'character': {'name': 'Dori'}})
    False
    """
    if isinstance(v, dict) and isinstance(w, dict):
        return all(
            cmp(v.get(k), w.get(k))
            for k in v.keys() & w.keys()
        )
    else:
        return v == w


def lit(s):
    """
    Matches a literal string, ignoring whitespace and casing (very useful for HTML fragments)
    >>> t = lit('<html>')
    >>> list(t('<!DOCTYPE html><html></html>'))
    [(False, '<html>', '<!DOCTYPE html><html></html>')]
    >>> list(t('<html></html>'))
    [(True, {}, '</html>')]
    >>> t = lit('<link href="foo">')
    >>> list(t('<link  href="foo">'))
    [(True, {}, '')]
    >>> list(t('  <LINK  href="foo">  '))
    [(True, {}, '')]
    """
    p = parsing.reg(
        re.compile(r'\s*' + re.sub(r'(?:\\\s)+', r'\\s+', re.escape(s.strip())) + r'\s*', flags=re.IGNORECASE)
    )
    return lambda x: (
        (True, {}, y) if m else (False, s, y)
        for m, v, y in p(x)
    )


def safe(k):
    """
    Matches a value for a variable reference, returning a context with that variable, prefering shorter values
    >>> t = safe('name')
    >>> list(t('Ori'))
    [(True, {'name': ''}, 'Ori'), (True, {'name': 'O'}, 'ri'), (True, {'name': 'Or'}, 'i'), (True, {'name': 'Ori'}, '')]
    """
    def p(x):
        v = ''
        while len(x) > 0:
            yield True, v, x
            v = v + x[0]
            x = x[1:]
        yield True, v, x

    return parsing.red(lambda v: ctx(k, ''.join(v)), p)


def var(k):
    """
    Matches a value for a variable reference, returning a context with that variable, prefering shorter values, HTML
    opening and closing brackets are not allowed (very useful for text between HTML tags)
    >>> t = var('name')
    >>> list(t('Ori'))
    [(True, {'name': ''}, 'Ori'), (True, {'name': 'O'}, 'ri'), (True, {'name': 'Or'}, 'i'), (True, {'name': 'Ori'}, '')]
    >>> t = var('mp')
    >>> list(t('0<BR>'))
    [(True, {'mp': ''}, '0<BR>'), (True, {'mp': '0'}, '<BR>')]
    """
    def p(x):
        v = ''
        while len(x) > 0 and x[0] not in '<>':
            yield True, v, x
            v = v + x[0]
            x = x[1:]
        yield True, v, x

    return parsing.red(lambda v: ctx(k, ''.join(v)), p)


def seq(p, q):
    """
    Matches p followed by q, combining the contexts they produce
    >>> t = seq(lit('<h2>'), seq(var('name'), lit('</h2>')))
    >>> [(m, v, y) for m, v, y in t('<h2>Ori</h2>') if m]
    [(True, {'name': 'Ori'}, '')]
    >>> t = seq(lit('<a href="'), seq(var('name'), seq(lit('">'), seq(var('name'), lit('</a>')))))
    >>> [(m, v, y) for m, v, y in t('<a href="atscreat.html">atsminions.html</a>') if y == '']
    [(False, '(predicate)', '')]
    """
    return parsing.red(lambda v: cmb(*v), parsing.grd(lambda v: cmp(*v), parsing.seq(p, q)))


def lst(k, l, p):
    """
    Matches 0 or more repetitions of p, extracting values of l and assigning them to the list k
    >>> t = seq(lit('<body>'), seq(lst('names', 'name', seq(lit('<h2>'), seq(safe('name'), lit('</h2>')))), lit('</body>')))
    >>> [(m, v, y) for m, v, y in t('<body><h2>Ori</h2></body>') if m]
    [(True, {'names': ['Ori']}, '')]
    >>> [(m, v, y) for m, v, y in t('<body><h2>Ori</h2><h2>Dori</h2></body>') if m]
    [(True, {'names': ['Ori', 'Dori']}, ''), (True, {'names': ['Ori</h2><h2>Dori']}, '')]
    >>> t = seq(lit('<body>'), seq(lst('character.names', 'name', seq(lit('<h2>'), seq(var('name'), lit('</h2>')))), lit('</body>')))
    >>> [(m, v, y) for m, v, y in t('<body><h2>Ori</h2></body>') if m]
    [(True, {'character': {'names': ['Ori']}}, '')]
    """
    return parsing.red(lambda v: ctx(k, [w[l] for w in v]), parsing.rep(p))


def iff(k, w, p, q):
    """
    Matches either p or q, with a preference for p; if it matches p, it assigns default value w to k
    >>> t = iff('card.playable', None, lit(''), seq(lit('Playable: '), seq(var('card.playable'), lit('<p>'))))
    >>> [(m, v, y) for m, v, y in t('Playable: Free-hold<p>Unique.') if m]
    [(True, {'card': {'playable': None}}, 'Playable: Free-hold<p>Unique.'), (True, {'card': {'playable': 'Free-hold'}}, 'Unique.')]
    >>> [(m, v, y) for m, v, y in t('Unique.') if m]
    [(True, {'card': {'playable': None}}, 'Unique.')]
    """
    # return parsing.alt(parsing.red(lambda v: cmb(ctx(k, w), v), p), q)
    # TODO: goed over nadenken en tests aanpassen
    # het idee is dat je juist de voorkeur hebt aan de branch waar geen default aan zit:
    #   - voor x == 'a' betekent dat lazy, en dat is niet erg want het is vaak een uniek fragment, of een soort switch
    #   - voor x is not none betekent dat eager, en dat helpt bij "CORRUPTION: {{ card.corruption }}<BR>"
    # misschien moet ik lst ook eager maken
    return parsing.alt(q, parsing.red(lambda v: cmb(ctx(k, w), v), p))


def parser(p):
    """
    Tries to match p to the entire input string; returns True and the resulting context if this succeeds, returns False
    and a useful error message when this fails.

    :param p: a parser like the one returned from the parsing combinators in this module
    :return: success, result

    >>> t = var('name')
    >>> p = parser(t)
    >>> p('Ori')
    (True, {'name': 'Ori'})
    >>> t = lit('Dori')
    >>> p = parser(t)
    >>> p('Ori')
    (False, "Expected 'Dori' at 1:1")
    """
    def q(x):
        failures = []
        min_fail_length = 0
        for m, v, y in p(x):
            if m and y == '':
                return True, v

            if not m:
                fail_length = len(x) - len(y)

                if fail_length > min_fail_length:
                    failures.clear()
                    min_fail_length = fail_length

                if fail_length == min_fail_length:
                    failures.append(v)

        expected = ', '.join(set(repr(v) for v in failures))
        recognized_string = x[0:min_fail_length]
        lines = recognized_string.split('\n')
        line = len(lines)
        char = len(lines[-1]) + 1

        return False, f'Expected {expected} at {line}:{char}'

    return q


if __name__ == '__main__':
    import doctest

    doctest.testmod()
