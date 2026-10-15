# Assumptions

Every rule reading Loopwright depends on. The code reads the config flag; change a default only when the Answer column is filled from an authoritative source.

| ID | Question | Default | Config flag | Answer | Source | Date |
|----|----------|---------|-------------|--------|--------|------|
| Q1 | Must a zone's rooms be joined by doors between themselves, or may the link pass through a room of another zone (usually the living room)? | strict | `zone_link = "strict"` (also `"circulation"`, `"through_rooms"`) | | | |
| Q2 | What exactly is J: its terms and weights? | J = L + 0.3·B + 3·X + 2·O, in metres | `bend_m = 0.3`, `crossing_m = 3`, `overlap_factor = 2` | | | |
| Q3 | Does a turn at a node count as a bend? Are two parallel runs through one door an overlap? Do crossings within one ring count? | Turns at nodes count; lanes at least 0.4 m apart are not overlap; crossings count within and between rings | `bend_at_node = true`, `lane_gap_m = 0.4`, `count_self_crossings = true` | | | |
| Q4 | Is the cap 5 nodes per hub (deck) or 20 devices (written statement)? | 5 | `max_nodes = 5` | | | |
| Q5 | What does the organisers' JSON look like: keys, geometry encoding, units? Does it give node positions? | ResPlan keys; scale from area | `input_format = "auto"` | | | |
| Q6 | If node positions are ours to choose, is any fixed rule acceptable? | Pole of inaccessibility, 0.5 m from walls where possible | `node_rule = "pole"` | | | |
| Q7 | Must a hub be on a wall? Is there a minimum distance between a hub and a node? | Anywhere inside an eligible room of its own zone; no minimum | `hub_mount = "free"`, `min_hub_node_m = 0` | | | |
| Q8 | May cables pass through bathrooms, corridors, stairs and rooms of other zones? | Yes, as pass-through without nodes | `pass_through = ["circulation", "bathroom", "stair", "other_zones"]` | | | |
| Q9 | When ResPlan draws the living room in pieces, is it one room? | One room (ResPlan's own convention; 231 plans) | `living_pieces = "merge"` | | | |
| Q10 | For angled walls, does "horizontal and vertical" mean the drawing's axes? | The drawing's axes | `axis_frame = "drawing"` | | | |
| Q11 | What should the output be when no valid design exists, for example a room over 100 m²? | Flag infeasible, plus a relaxed design marked invalid | `infeasible_output = "flag_and_relaxed"` | | | |
| Q12 | How are entries scored: hidden plans, totals, per plan, or the demo? Is there a time limit? | Optimise totals; keep p95 under 2 s per plan | `time_limit_s = 10` | | | |
| Q13 | May code written before the 48 hours start be used? | No | (process, not code) | | | |
| Q14 | For the 100 m² cap, is room area the polygon area × scale², or the dimensions in the organisers' JSON? | Polygon area × scale² | `area_source = "polygon"` | | | |
