"""What a single cable break does to a closed ring.

A ring leaves its hub and comes back to it, so cutting any one leg still
leaves every node connected: the nodes before the cut are fed forward, the
nodes after it from the other end. For each possible cut this reports which
side feeds each node, the cable distance from the hub, and the longest feed,
which is the worst case for the loop's electrical budget.
"""


def _cuts(ring):
    nodes = ring["sequence"][1:-1]
    lengths = [leg["length_m"] for leg in ring["legs"]]
    forward = [sum(lengths[:j + 1]) for j in range(len(nodes))]
    reverse = [sum(lengths[j + 1:]) for j in range(len(nodes))]
    out = []
    for k in range(len(lengths)):
        # Leg k joins sequence[k] and sequence[k + 1]: nodes[:k] keep their forward feed.
        fwd = [{"node": nodes[j], "m": round(forward[j], 2)} for j in range(k)]
        rev = [{"node": nodes[j], "m": round(reverse[j], 2)} for j in range(len(nodes) - 1, k - 1, -1)]
        out.append({"leg": ring["legs"][k]["n"], "fed_forward": fwd, "fed_reverse": rev,
                    "farthest_m": max((f["m"] for f in fwd + rev), default=0.0)})
    return out


def cut_analysis(design):
    """{hub id: [one entry per leg, in ring order]} for every ring of a loopwright/2 design."""
    return {ring["hub"]: _cuts(ring) for ring in design["rings"]}
