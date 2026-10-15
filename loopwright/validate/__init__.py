"""Independent validator and scorer (lane C).

Must not import loopwright.geometry, loopwright.routing or loopwright.optimize:
it rebuilds what it needs from the raw plan so it can catch solver bugs.
"""
