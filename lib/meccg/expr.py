import itertools


def var(k):
    return lambda c: c[k]


def lit(v):
    return lambda c: v


def star():
    return lambda c: c


def kvp(k, v):
    return lambda c: {k: v(c)}


def obj(es):
    return lambda c: {k: v for e in es for k, v in e(c).items()}


def el(v):
    return lambda c: [v(c)]


def arr(es):
    return lambda c: [v for e in es for v in e(c)]


def ter(d, l, r):
    return lambda c: l(c) if d(c) else r(c)


def bin(f, l, r):
    return lambda c: f(l(c), r(c))


def uni(f, o):
    return lambda c: f(o(c))


def ret(e):
    return lambda rs: (
        (e(r), r)
        for r in rs
    )


def grp_key(i):
    return lambda gc: gc['$keys'][i]


def grp_arr(e):
    return lambda gc: [
        e(c)
        for c in gc['$records']
    ]


def grp_ret(ke, ge):
    return lambda rs: (
        (ge(r), r)
        for gk, grs in itertools.groupby(rs, ke)
        for r in [{'$keys': gk, '$records': list(grs)}]
    )
