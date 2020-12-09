import re


def lit(s):
    """
    >>> p = lit('<html>')
    >>> p('<!DOCTYPE html><html></html>')
    [(False, '<html>', '<!DOCTYPE html><html></html>')]
    >>> p('<html></html>')
    [(True, '<html>', '</html>')]
    """
    return lambda x: \
        [(True, x[0:len(s)], x[len(s):])] if x.startswith(s) else [(False, s, x)]


def reg(s):
    """
    >>> p = reg(r'<\w+>')
    >>> p('<!DOCTYPE html><html></html>')
    [(False, '<\\\\w+>', '<!DOCTYPE html><html></html>')]
    >>> p('<html></html>')
    [(True, '<html>', '</html>')]
    >>> s = re.compile(r'\\<html\\>', flags=re.IGNORECASE)
    >>> p = reg(s)
    >>> p('<HTML></HTML>')
    [(True, '<HTML>', '</HTML>')]
    """
    return lambda x: \
        [(True, re.match(s, x)[0], x[len(re.match(s, x)[0]):])] if re.match(s, x) else [(False, s, x)]


def dot():
    """
    >>> p = dot()
    >>> p('')
    [(False, '(any character)', '')]
    >>> p('Alatar')
    [(True, 'A', 'latar')]
    """
    return lambda x: \
        [(True, x[0], x[1:])] if len(x) > 0 else [(False, '(any character)', x)]


def eps():
    """
    >>> p = eps()
    >>> p('</html>')
    [(True, '', '</html>')]
    >>> p('')
    [(True, '', '')]
    """
    return lambda x: \
        [(True, '', x)]


def alt(p, q):
    """
    >>> p = alt(lit('<html>'), lit('<body>'))
    >>> list(p('<!DOCTYPE html><html></html>'))
    [(False, '<html>', '<!DOCTYPE html><html></html>'), (False, '<body>', '<!DOCTYPE html><html></html>')]
    >>> list(p('<html></html>'))
    [(True, '<html>', '</html>'), (False, '<body>', '<html></html>')]
    >>> list(p('<body></body>'))
    [(False, '<html>', '<body></body>'), (True, '<body>', '</body>')]
    >>> p = alt(eps(), lit('<body>'))
    >>> list(p('<html></html>'))
    [(True, '', '<html></html>'), (False, '<body>', '<html></html>')]
    >>> list(p('<body></body>'))
    [(True, '', '<body></body>'), (True, '<body>', '</body>')]
    """
    return lambda x: (
        (m, v, y)
        for r in [p, q]
        for m, v, y in r(x)
    )


def seq(p, q):
    """
    >>> p = seq(lit('<html>'), lit('<body>'))
    >>> list(p('<!DOCTYPE html><html></html>'))
    [(False, '<html>', '<!DOCTYPE html><html></html>')]
    >>> list(p('<html>'))
    [(False, '<body>', '')]
    >>> list(p('<html><body></body></html>'))
    [(True, ('<html>', '<body>'), '</body></html>')]
    >>> p = seq(lit('<html>'), alt(eps(), lit('<body>')))
    >>> list(p('<html>'))
    [(True, ('<html>', ''), ''), (False, '<body>', '')]
    >>> list(p('<html><body></body></html>'))
    [(True, ('<html>', ''), '<body></body></html>'), (True, ('<html>', '<body>'), '</body></html>')]
    >>> p = seq(lit('<html>'), lit('<body>'))
    >>> list(p('<body><html></html>'))
    [(False, '<html>', '<body><html></html>')]
    """
    return lambda x: (
        (False, v, y) if not m else (False, w, z) if not n else (True, (v, w), z)
        for m, v, y in p(x)
        for n, w, z in (q(y) if m else [(None, None, None)])
    )


def red(f, p):
    """
    >>> p = red(lambda v: v.upper(), lit('<html>'))
    >>> list(p('<!DOCTYPE html><html></html>'))
    [(False, '<html>', '<!DOCTYPE html><html></html>')]
    >>> list(p('<html></html>'))
    [(True, '<HTML>', '</html>')]
    """
    return lambda x: (
        (m, f(v) if m else v, y)
        for m, v, y in p(x)
    )


def ref(f):
    return lambda x: f()(x)


def rep(p):
    """
    >>> p = rep(dot())
    >>> list(p('Ori'))
    [(True, [], 'Ori'), (True, ['O'], 'ri'), (True, ['O', 'r'], 'i'), (True, ['O', 'r', 'i'], ''), (False, '(any character)', '')]
    """
    def f():
        return alt(
            red(lambda v: [], eps()),
            red(lambda v: [v[0]] + v[1], seq(p, ref(f)))
        )

    return ref(f)


if __name__ == '__main__':
    import doctest

    doctest.testmod()
