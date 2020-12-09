import re

import lib.meccg.parsing as parsing


def ctx(k, v):
    """
    >>> ctx('name', 'Ori')
    {'name': 'Ori'}
    >>> ctx('character.name', 'Ori')
    {'character': {'name': 'Ori'}}
    """
    return ctx(k.split('.')[0], ctx(k.split('.')[1], v)) if '.' in k else {k: v}


def cmb(v, w):
    """
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


def lit(s):
    """
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
    >>> t = seq(lit('<h2>'), seq(var('name'), lit('</h2>')))
    >>> [(m, v, y) for m, v, y in t('<h2>Ori</h2>') if m]
    [(True, {'name': 'Ori'}, '')]
    """
    return parsing.red(lambda v: cmb(*v), parsing.seq(p, q))


def lst(k, l, p):
    """
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
    >>> t = iff('card.playable', '', lit(''), seq(lit('Playable: '), seq(var('card.playable'), lit('<p>'))))
    >>> [(m, v, y) for m, v, y in t('Playable: Free-hold<p>Unique.') if m]
    [(True, {'card': {'playable': ''}}, 'Playable: Free-hold<p>Unique.'), (True, {'card': {'playable': 'Free-hold'}}, 'Unique.')]
    >>> [(m, v, y) for m, v, y in t('Unique.') if m]
    [(True, {'card': {'playable': ''}}, 'Unique.')]
    """
    return parsing.alt(parsing.red(lambda v: cmb(ctx(k, w), v), p), q)


def parser(p):
    """
    >>> t = var('name')
    >>> p = parser(t)
    >>> p('Ori')
    {'name': 'Ori'}
    >>> t = lit('Dori')
    >>> p = parser(t)
    >>> p('Ori')
    (['Dori'], 'Ori')
    """
    def q(x):
        failures = []
        for m, v, y in p(x):
            if m and y == '':
                return True, v

            if not m:
                failures.append((v, y))

        min_fail_length = min(len(y) for v, y in failures)
        first_failures = [(v, y) for v, y in failures if len(y) == min_fail_length]
        expected = ', '.join(set(repr(v) for v, y in first_failures))
        recognized_string = x[0:-len(first_failures[0][1])]
        lines = recognized_string.split('\n')
        line = len(lines)
        char = len(lines[-1])

        return False, f'Expected {expected} at {line}:{char}'

        return [v for v, y in first_failures], next(y for v, y in first_failures)

    return q
    return lambda x: \
        next((v for m, v, y in p(x) if y == ''), None)


if __name__ == '__main__':
    import doctest

    doctest.testmod()
