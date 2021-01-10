import re
from html import unescape

from meccg import sat


def lit(s):
    """
    Matches a literal string s (without white space tolerance, etc.)
    >>> t = lit(' ')
    >>> list(t({'dummy': None}, 'Scout Hobbit'))
    [(False, ' ', 'Scout Hobbit')]
    >>> list(t({'dummy': None}, ' Hobbit'))
    [(True, {'dummy': None}, 'Hobbit')]
    """
    return lambda c, x: \
        [(True, c, x[len(s):])] if x.startswith(s) \
        else [(False, s, x)]


def html(s):
    """
    Matches an HTML string s, ignoring whitespace and casing
    >>> t = html('<html>')
    >>> list(t({'dummy': None}, '<!DOCTYPE html><html></html>'))
    [(False, '<html>', '<!DOCTYPE html><html></html>')]
    >>> list(t({'dummy': None}, '<html></html>'))
    [(True, {'dummy': None}, '</html>')]
    >>> t = html('<link href="foo" >')
    >>> list(t({'dummy': None}, '  < LINK  href="foo">  '))
    [(True, {'dummy': None}, '')]
    """
    pattern = s.strip()
    pattern = re.sub(r'\s*<\s*', '<', pattern)
    pattern = re.sub(r'\s*>\s*', '>', pattern)
    pattern = re.escape(pattern)
    pattern = re.sub(r'(?:\\\s)+', r'\\s+', pattern)
    pattern = re.sub(r'<', r'\\s*<\\s*', pattern)
    pattern = re.sub(r'>', r'\\s*>\\s*', pattern)
    pattern = '\\s*' + pattern + '\\s*'
    pattern_object = re.compile(pattern, flags=re.IGNORECASE)
    return lambda c, x: \
        [(True, c, x[len(pattern_object.match(x)[0]):])] if pattern_object.match(x) \
        else [(False, s.strip(), x)]


def var(r, f, k):
    """
    Matches a string into a variable k, applying filter f, rejecting characters r, with a preferce for shorter values
    (and only if the variable matches the input context)
    """
    def p(c, x):
        v = ''
        y = x
        while len(y) > 0 and y[0] not in r:
            d = sat.ctx(k, f(v))
            if sat.cmp(c, d):
                yield True, sat.cmb(c, d), y
            # note: not yielding a failure here, because it would be either:
            #   - unnecessary because of a match at the end
            #   - identical to the failure yielded at the end
            v = v + y[0]
            y = y[1:]
        d = sat.ctx(k, f(v))
        if sat.cmp(c, d):
            yield True, sat.cmb(c, d), y
        else:
            yield False, sat.get(k, c), x

    return p


def safe(k):
    """
    Matches any string into a variable k
    >>> t = safe('name')
    >>> list(t({'dummy': None}, 'Ori'))  # doctest: +ELLIPSIS
    [(True, {'dummy': None, 'name': ''}, 'Ori'), ..., (True, {'dummy': None, 'name': 'Ori'}, '')]
    >>> list(t({'dummy': None, 'name': 'Dori'}, 'Ori'))  # doctest: +ELLIPSIS
    [(False, 'Dori', 'Ori')]
    >>> list(t({'dummy': None, 'name': 'Ori'}, 'Ori'))  # doctest: +ELLIPSIS
    [(True, {'dummy': None, 'name': 'Ori'}, '')]
    >>> list(t({'dummy': None, 'name': 'Ori'}, 'Ori<br>'))  # doctest: +ELLIPSIS
    [(True, {'dummy': None, 'name': 'Ori'}, '<br>'), (False, 'Ori', 'Ori<br>')]
    """
    return var('', lambda v: v, k)


def esc(k):
    """
    Matches a string without tags into a variable k, unescaping the result
    >>> t = esc('name')
    >>> list(t({}, 'Ori'))
    [(True, {'name': ''}, 'Ori'), (True, {'name': 'O'}, 'ri'), (True, {'name': 'Or'}, 'i'), (True, {'name': 'Ori'}, '')]
    >>> t = esc('mp')
    >>> list(t({}, '0<BR>'))
    [(True, {'mp': ''}, '0<BR>'), (True, {'mp': '0'}, '<BR>')]
    >>> list(t({}, '&lt;'))  # doctest: +ELLIPSIS
    [(True, {'mp': ''}, '&lt;'), (True, {'mp': '&'}, 'lt;'), ..., (True, {'mp': '<'}, '')]
    """
    return var('<>', unescape, k)


def flt(f, k):
    """
    Matches a string without tags into a variable k, unescaping the result, and then applying filter f
    >>> t = flt(lambda x: x.replace('Dw.', 'Dwarven'), 'name')
    >>> list(t({}, 'Dw. Ring of Barin&apos;s Tribe'))  # doctest: +ELLIPSIS
    [(True, {'name': ''}, 'Dw. Ring of Barin&apos;s Tribe'), ..., (True, {'name': "Dwarven Ring of Barin's Tribe"}, '')]
    """
    return var('<>', lambda v: f(unescape(v)), k)


def alt(p, q):
    """
    Matches either p or q, with a preference for p
    >>> t = alt(html('<h2>'), html('<br>'))
    >>> list(t({}, '<br>'))
    [(False, '<h2>', '<br>'), (True, {}, '')]
    >>> list(t({}, '<h2>'))
    [(True, {}, ''), (False, '<br>', '<h2>')]
    >>> list(t({}, 'Ori<br>'))
    [(False, '<h2>', 'Ori<br>'), (False, '<br>', 'Ori<br>')]
    """
    def r(c, x):
        for m, d, y in p(c, x):
            yield m, d, y
        for m, d, y in q(c, x):
            yield m, d, y

    return r


def seq(p, q):
    """
    Matches p followed by q, passing the resulting context of p to q
    >>> t = seq(esc('name'), html('<br>'))
    >>> list(t({}, 'Ori<br>'))
    [(False, '<br>', 'Ori<br>'), (False, '<br>', 'ri<br>'), (False, '<br>', 'i<br>'), (True, {'name': 'Ori'}, '')]
    >>> list(t({'name': 'Dori'}, 'Ori<br>'))
    [(False, 'Dori', 'Ori<br>')]
    """
    def r(c, x):
        for m, d, y in p(c, x):
            if m:
                for n, e, z in q(d, y):
                    yield n, e, z
            else:
                yield m, d, y

    return r


def eps():
    """
    Matches an empty string
    >>> t = eps()
    >>> t({'dummy': None}, 'Ori')
    [(True, {'dummy': None}, 'Ori')]
    """
    return lambda c, x: [(True, c, x)]


def let(f, p):
    """
    For each constraint returned by f, check if the constraint is compatible with the input context. If so, add the
    constraints and continue with p (f may return a generator)
    >>> t = let(lambda: [{'name': 'Ori'}, {'name': 'Dori'}], esc('name'))
    >>> list(t({}, 'Ori'))
    [(True, {'name': 'Ori'}, ''), (False, 'Dori', 'Ori')]
    >>> list(t({}, 'Dori'))
    [(False, 'Ori', 'Dori'), (True, {'name': 'Dori'}, '')]
    >>> list(t({}, 'Nori'))
    [(False, 'Ori', 'Nori'), (False, 'Dori', 'Nori')]
    >>> t = let(lambda: [{'name': 'Ori'}], esc('text'))
    >>> list(t({}, 'Unique.<br>'))  # doctest: +ELLIPSIS
    [(True, {'name': 'Ori', 'text': ''}, 'Unique.<br>'), ..., (True, {'name': 'Ori', 'text': 'Unique.'}, '<br>')]
    """
    def q(c, x):
        for d in f():
            if sat.cmp(c, d):
                for n, e, y in p(sat.cmb(c, d), x):
                    yield n, e, y
            else:
                yield False, '(constraint)', x

    return q


def ref(f):
    """
    Matches the parser returned by f, can be used for recursion
    """
    return lambda c, x: f()(c, x)


def lst(k, l, p):
    """
    Matches 0 or more repetitions of p, extracting values of l and assigning them to the list k
    >>> t = seq(html('<body>'), seq(lst('names', 'name', seq(html('<h2>'), seq(safe('name'), html('</h2>')))), html('</body>')))
    >>> [(m, v, y) for m, v, y in t({}, '<body><h2>Ori</h2></body>') if m]
    [(True, {'names': ['Ori']}, '')]
    >>> [(m, v, y) for m, v, y in t({}, '<body><h2>Ori</h2><h2>Dori</h2></body>') if m]
    [(True, {'names': ['Ori', 'Dori']}, ''), (True, {'names': ['Ori</h2><h2>Dori']}, '')]
    >>> t = seq(html('<body>'), seq(lst('character.names', 'name', seq(html('<h2>'), seq(esc('name'), html('</h2>')))), html('</body>')))
    >>> [(m, v, y) for m, v, y in t({}, '<body><h2>Ori</h2></body>') if m]
    [(True, {'character': {'names': ['Ori']}}, '')]
    >>> t = lst('names', 'name', seq(lit('<'), seq(esc('tag'), seq(lit('>'), seq(esc('name'), seq(lit('</'), seq(esc('tag'), lit('>'))))))))
    >>> [(m, v, y) for m, v, y in t({}, '<h2>Ori</h2><h2>Dori</h2>') if m and y == '']
    [(True, {'names': ['Ori', 'Dori'], 'tag': 'h2'}, '')]
    >>> [(m, v, y) for m, v, y in t({}, '<h1>Ori</h1><h2>Dori</h2>') if m]
    [(True, {'names': ['Ori'], 'tag': 'h1'}, '<h2>Dori</h2>'), (True, {'names': []}, '<h1>Ori</h1><h2>Dori</h2>')]
    """
    def q(c, x):
        for m, d, y in p(c, x):
            if m:
                v = sat.get(l, d)
                e = sat.rem(l, sat.upd(k, lambda w: w + [v], d))
                yield True, e, y
            else:
                yield m, d, y

    def f():
        return alt(
            seq(q, ref(f)),
            eps()
        )

    return let(lambda: [sat.ctx(k, [])], ref(f))


def iff(e, p, q):
    """
    Matches either p or q, with a preference for p; for p, it assigns all positive solutions of expression e; for q it
    assigns negative solutions
    >>> t = iff(sat.neg(sat.eq('card.playable', None)), seq(html('Playable: '), seq(esc('card.playable'), html('<p>'))), eps())
    >>> [(m, v, y) for m, v, y in t({}, 'Playable: Free-hold<p>Unique.') if m]
    [(True, {'card': {'playable': 'Free-hold'}}, 'Unique.'), (True, {'card': {'playable': None}}, 'Playable: Free-hold<p>Unique.')]
    >>> [(m, v, y) for m, v, y in t({}, 'Unique.') if m]
    [(True, {'card': {'playable': None}}, 'Unique.')]
    """
    return alt(let(lambda: e(True), p), let(lambda: e(False), q))


def parser(p, max_tries=None):
    """
    Tries to match p to the entire input string; returns True and the resulting context if this succeeds, returns False
    and a useful error message when this fails.

    :param p: a parser like the one returned from the parsing combinators in this module
    :param max_tries: the maximum number of failures before giving up (default to None, in which case we never give up)
    :return: success, result

    >>> t = esc('name')
    >>> p = parser(t)
    >>> p('Ori')
    (True, {'name': 'Ori'})
    >>> t = lit('Dori')
    >>> p = parser(t)
    >>> p('Ori')
    (False, "Expected 'Dori' at 1:1")
    >>> p('Dori</h2>')
    (False, 'Expected end of file at 1:5')
    >>> t = seq(esc('skills'), seq(lit(' '), esc('race')))
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
        for m, v, y in p({}, x):
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

        expected = ', '.join(sorted(set(failures)))
        recognized_string = x[0:min_fail_length]
        lines = recognized_string.split('\n')
        line = len(lines)
        char = len(lines[-1]) + 1

        return False, f'Expected {expected} at {line}:{char}'

    return q
