"""Why a design has the hubs it has, in one sentence, from the design's own numbers."""
import math


def explain_hubs(design):
    """{"binding": ..., "rooms": [...], "text": ...} for a loopwright/2 design."""
    rules, metrics = design["rules"], design["metrics"]
    cap_area, cap_nodes = rules["max_area_m2"], rules["max_nodes"]
    hubs, lb = metrics["hubs"], metrics["hub_lower_bound"]
    eligible = [r for r in design["rooms"] if r["eligible"]]
    area, n = sum(r["area_m2"] for r in eligible), len(eligible)
    diag = design.get("diagnostics", [])

    over = [d for d in diag if d["code"] == "ROOM_OVER_CAP"]
    if over:
        names = ", ".join(f"{d['room']} ({d['area_m2']} m²)" for d in over)
        return {"binding": "room over cap", "rooms": [d["room"] for d in over],
                "text": f"No valid design exists: {names} is over the {cap_area:g} m² cap for one hub."}

    if hubs > lb:
        extra = [d for d in diag if d["code"] == "EXTRA_HUB"]
        reasons = "; ".join(f"{d['room']} {d['reason']}" for d in extra)
        return {"binding": "door links", "rooms": [d["room"] for d in extra],
                "text": f"{hubs} hubs against a lower bound of {lb}: under the '{rules['zone_link']}' zone rule "
                        f"some rooms can't share a hub. {reasons}."}

    if hubs <= 1:
        return {"binding": "one zone", "rooms": [],
                "text": f"1 hub: all {n} rooms ({area:.0f} m²) fit one zone of at most {cap_area:g} m² and {cap_nodes} nodes."}

    by_area, by_nodes = math.ceil(round(area / cap_area, 9)), math.ceil(n / cap_nodes)
    if by_nodes > by_area:
        return {"binding": "nodes", "rooms": [],
                "text": f"{hubs} hubs, the minimum possible: {n} rooms need at least {by_nodes} at {cap_nodes} per hub."}
    return {"binding": "area", "rooms": [],
            "text": f"{hubs} hubs, the minimum possible: {area:.0f} m² of eligible rooms needs at least {by_area} "
                    f"at {cap_area:g} m² per hub."}
