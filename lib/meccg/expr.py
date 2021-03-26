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


def bin(f, l, r):
    return lambda c: f(l(c), r(c))


def uni(f, o):
    return lambda c: f(o(c))
