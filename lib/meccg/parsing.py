import re


def lit(s):
    """
    Matches a literal string
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
    Matches a regular expression
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
    Matches any one character
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
    Matches an empty string
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
    Matches either p or q, with preference for p
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
    Matches p followed by q
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
    Matches p and maps the result
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


def grd(f, p):
    """
    Matches p, but only if the predicate f holds
    >>> p = grd(lambda v: v.upper() == v, dot())
    >>> list(p(''))
    [(False, '(any character)', '')]
    >>> list(p('Alatar'))
    [(True, 'A', 'latar')]
    >>> list(p('alatar'))
    [(False, '(predicate)', 'latar')]
    """
    return lambda x: (
        (m and f(v), '(predicate)' if m and not f(v) else v, y)
        for m, v, y in p(x)
        # if not m or f(v)
    )


def ref(f):
    """
    Matches the parser returned by f, can be used for recursion
    """
    return lambda x: f()(x)


def rep(p):
    """
    Matches 0 or more repetitions of p, with preference for less
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
