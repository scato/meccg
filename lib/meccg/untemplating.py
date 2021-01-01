import re
from html import unescape

import meccg.parsing as parsing
import meccg.sat as sat


def vrb(s):
    """
    Matches a literal string, ad verbatim
    >>> t = vrb(' ')
    >>> list(t('Scout Hobbit'))
    [(False, ' ', 'Scout Hobbit')]
    >>> list(t(' Hobbit'))
    [(True, {}, 'Hobbit')]
    """
    return parsing.red(lambda v: {}, parsing.lit(s))


def lit(s):
    """
    Matches a literal string, ignoring whitespace and casing (very useful for HTML fragments)
    >>> t = lit('<html>')
    >>> list(t('<!DOCTYPE html><html></html>'))
    [(False, '<html>', '<!DOCTYPE html><html></html>')]
    >>> list(t('<html></html>'))
    [(True, {}, '</html>')]
    >>> t = lit('<link href="foo" >')
    >>> list(t('  < LINK  href="foo">  '))
    [(True, {}, '')]
    """
    e = s.strip()
    e = re.sub(r'\s*<\s*', '<', e)
    e = re.sub(r'\s*>\s*', '>', e)
    e = re.escape(e)
    e = re.sub(r'(?:\\\s)+', r'\\s+', e)
    e = re.sub(r'<', r'\\s*<\\s*', e)
    e = re.sub(r'>', r'\\s*>\\s*', e)
    e = '\\s*' + e + '\\s*'
    p = parsing.reg(
        re.compile(e, flags=re.IGNORECASE)
    )
    return lambda x: (
        (True, {}, y) if m else (False, s.strip(), y)
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

    return parsing.red(lambda v: sat.ctx(k, ''.join(v)), p)


def var(k):
    """
    Matches a value for a variable reference, returning a context with that variable and the unescaped input, prefering
    shorter values, HTML opening and closing brackets are not allowed (very useful for text between HTML tags)
    >>> t = var('name')
    >>> list(t('Ori'))
    [(True, {'name': ''}, 'Ori'), (True, {'name': 'O'}, 'ri'), (True, {'name': 'Or'}, 'i'), (True, {'name': 'Ori'}, '')]
    >>> t = var('mp')
    >>> list(t('0<BR>'))
    [(True, {'mp': ''}, '0<BR>'), (True, {'mp': '0'}, '<BR>')]
    >>> list(t('0 <BR>'))
    [(True, {'mp': ''}, '0 <BR>'), (True, {'mp': '0'}, ' <BR>')]
    >>> list(t('&lt;'))  # doctest: +ELLIPSIS
    [(True, {'mp': ''}, '&lt;'), (True, {'mp': '&'}, 'lt;'), ..., (True, {'mp': '<'}, '')]
    """
    return flt(unescape, k)


def flt(f, k):
    def p(x):
        v = ''
        while len(x) > 0 and x[0] not in '<>':
            if not v.endswith(' '):
                yield True, v, x
            v = v + x[0]
            x = x[1:]
        if not v.endswith(' '):
            yield True, v, x

    return parsing.red(lambda v: sat.ctx(k, f(v)), p)


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
    return parsing.red(lambda v: sat.cmb(*v), parsing.grd(lambda v: sat.cmp(*v), parsing.seq(p, q)))


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
    return parsing.red(lambda v: sat.ctx(k, [w[l] for w in v]), parsing.rep(p))


def iff(e, p, q):
    """
    Matches either p or q, with a preference for p; if it matches p, it assigns default value w to k
    >>> from meccg import sat
    >>> t = iff(sat.neg(sat.eq('card.playable', None)), seq(lit('Playable: '), seq(var('card.playable'), lit('<p>'))), lit(''))
    >>> [(m, v, y) for m, v, y in t('Playable: Free-hold<p>Unique.') if m]
    [(True, {'card': {'playable': 'Free-hold'}}, 'Unique.'), (True, {'card': {'playable': None}}, 'Playable: Free-hold<p>Unique.')]
    >>> [(m, v, y) for m, v, y in t('Unique.') if m]
    [(True, {'card': {'playable': None}}, 'Unique.')]
    """
    return parsing.alt(
        lambda x: (
            (m, sat.cmb(v, w) if m else v, y)
            for m, v, y in p(x)
            for w in e(True)
            if sat.cmp(v, w)
        ),
        lambda x: (
            (m, sat.cmb(v, w) if m else v, y)
            for m, v, y in q(x)
            for w in e(False)
            if sat.cmp(v, w)
        )
    )


def parser(p, max_tries=None):
    """
    Tries to match p to the entire input string; returns True and the resulting context if this succeeds, returns False
    and a useful error message when this fails.

    :param p: a parser like the one returned from the parsing combinators in this module
    :param max_tries: the maximum number of failures before giving up (default to None, in which case we never give up)
    :return: success, result

    >>> t = var('name')
    >>> p = parser(t)
    >>> p('Ori')
    (True, {'name': 'Ori'})
    >>> t = lit('Dori')
    >>> p = parser(t)
    >>> p('Ori')
    (False, "Expected 'Dori' at 1:1")
    >>> p('Dori</h2>')
    (False, 'Expected end of file at 1:5')
    >>> t = seq(var('skills'), seq(vrb(' '), var('race')))
    >>> p = parser(t)
    >>> p('Warrior Dwarf')
    (True, {'race': 'Dwarf', 'skills': 'Warrior'})
    >>> p = parser(t, max_tries=5)
    >>> p('Warrior Dwarf')
    (False, "Expected ' ' at 1:7")
    >>> p = parser(t, max_tries=6)
    >>> p('Warrior Dwarf')
    (False, 'Expected end of file at 1:9')
    """
    def q(x):
        failures = []
        min_fail_length = 0
        num_tries = 0
        for m, v, y in p(x):
            if m and y == '':
                return True, v
            else:
                fail_length = len(x) - len(y)

                if fail_length > min_fail_length:
                    failures.clear()
                    min_fail_length = fail_length

                if fail_length == min_fail_length:
                    failures.append(repr(v) if not m else 'end of file')

            if max_tries is not None:
                if num_tries > max_tries:
                    break
                else:
                    num_tries += 1

        expected = ', '.join(set(failures))
        recognized_string = x[0:min_fail_length]
        lines = recognized_string.split('\n')
        line = len(lines)
        char = len(lines[-1]) + 1

        return False, f'Expected {expected} at {line}:{char}'

    return q


if __name__ == '__main__':
    import doctest

    doctest.testmod()
