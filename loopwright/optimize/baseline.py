"""Greedy zoning baseline, used only to show what the exact search saves.

Seed the largest unassigned room, then keep adding the largest directly linked
room that fits both caps. Measured on all 16,556 feasible ResPlan plans (strict
rule, Phase 14): 31,052 hubs against the exact 29,369.
"""


def greedy_zones(room_ids, areas, adj, settings):
    area_of = dict(zip(room_ids, areas))
    left = set(room_ids)
    zones = []
    while left:
        seed = max(sorted(left), key=lambda r: area_of[r])
        zone, total = [seed], area_of[seed]
        left.discard(seed)
        grew = True
        while grew and len(zone) < settings.max_nodes:
            grew = False
            frontier = sorted({v for u in zone for v in adj.get(u, ()) if v in left},
                              key=lambda r: (-area_of[r], r))
            for room in frontier:
                if total + area_of[room] <= settings.max_area_m2 + 1e-9:
                    zone.append(room)
                    left.discard(room)
                    total += area_of[room]
                    grew = True
                    break
        zones.append(zone)
    return zones
