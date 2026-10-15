"""Every rule reading as a setting. Defaults mirror docs/assumptions.md (Q1-Q14).

Solver code reads these settings; it never hard-codes a rule reading. When an
answer arrives from the organisers, change the default here in its own commit
and record the answer in docs/assumptions.md.
"""
from dataclasses import dataclass, fields, replace

ZONE_LINKS = ("strict", "circulation", "through_rooms")


@dataclass(frozen=True)
class Settings:
    # Q1: how a zone's rooms must be joined
    zone_link: str = "strict"
    # Q2: weights in J = L + bend_m*B + crossing_m*X + overlap_factor*O
    bend_m: float = 0.3
    crossing_m: float = 3.0
    overlap_factor: float = 2.0
    # Q3: what counts as a bend, an overlap, a crossing
    bend_at_node: bool = True
    lane_gap_m: float = 0.4
    count_self_crossings: bool = True
    # Q4 and the area cap
    max_nodes: int = 5
    max_area_m2: float = 100.0
    # Q5-Q14
    input_format: str = "auto"
    node_rule: str = "pole"
    hub_mount: str = "free"
    min_hub_node_m: float = 0.0
    pass_through: tuple = ("circulation", "bathroom", "stair", "other_zones")
    living_pieces: str = "merge"
    axis_frame: str = "drawing"
    infeasible_output: str = "flag_and_relaxed"
    time_limit_s: float = 10.0
    area_source: str = "polygon"
    # Geometry constants (not rule readings)
    clearance_m: float = 0.10
    sliver_m2: float = 0.5

    def __post_init__(self):
        if self.zone_link not in ZONE_LINKS:
            raise ValueError(f"zone_link must be one of {ZONE_LINKS}, got {self.zone_link!r}")
        if self.max_nodes < 1 or self.max_area_m2 <= 0:
            raise ValueError("caps must be positive")

    def with_overrides(self, **kw):
        known = {f.name for f in fields(self)}
        unknown = set(kw) - known
        if unknown:
            raise ValueError(f"unknown settings: {sorted(unknown)}")
        return replace(self, **{k: v for k, v in kw.items() if v is not None})

    def as_dict(self):
        return {f.name: getattr(self, f.name) for f in fields(self)}


DEFAULT = Settings()
