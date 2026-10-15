from dataclasses import dataclass, fields, replace
import math


ZONE_LINKS = ("strict", "circulation", "through_rooms")
PASS_THROUGH = ("circulation", "bathroom", "stair", "other_zones")
INPUT_FORMATS = ("auto", "json", "resplan")
NODE_RULES = ("pole",)
HUB_MOUNTS = ("free",)
LIVING_PIECES = ("merge", "separate")
AXIS_FRAMES = ("drawing",)
INFEASIBLE_OUTPUTS = ("flag_and_relaxed",)
AREA_SOURCES = ("polygon",)


def _finite_number(name, value, minimum=None, *, strictly_positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if strictly_positive and value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _choice(name, value, choices):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of {choices}, got {value!r}")


def _boolean(name, value):
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class Settings:
    zone_link: str = "strict"
    bend_m: float = 0.3
    crossing_m: float = 3.0
    overlap_factor: float = 2.0
    bend_at_node: bool = True
    lane_gap_m: float = 0.4
    count_self_crossings: bool = True
    max_nodes: int = 5
    max_area_m2: float = 100.0
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
    clearance_m: float = 0.10
    sliver_m2: float = 0.5

    def __post_init__(self):
        _choice("zone_link", self.zone_link, ZONE_LINKS)
        _finite_number("bend_m", self.bend_m, 0)
        _finite_number("crossing_m", self.crossing_m, 0)
        _finite_number("overlap_factor", self.overlap_factor, 0)
        _boolean("bend_at_node", self.bend_at_node)
        _finite_number("lane_gap_m", self.lane_gap_m, 0)
        _boolean("count_self_crossings", self.count_self_crossings)
        if type(self.max_nodes) is not int or self.max_nodes < 1:
            raise ValueError("max_nodes must be a positive integer")
        _finite_number("max_area_m2", self.max_area_m2, strictly_positive=True)
        _choice("input_format", self.input_format, INPUT_FORMATS)
        _choice("node_rule", self.node_rule, NODE_RULES)
        _choice("hub_mount", self.hub_mount, HUB_MOUNTS)
        _finite_number("min_hub_node_m", self.min_hub_node_m, 0)

        if isinstance(self.pass_through, (str, bytes)):
            raise ValueError("pass_through must be a sequence of room classes")
        try:
            pass_through = tuple(self.pass_through)
        except TypeError as exc:
            raise ValueError("pass_through must be a sequence of room classes") from exc
        if any(room_class not in PASS_THROUGH for room_class in pass_through):
            raise ValueError(f"pass_through must contain only values from {PASS_THROUGH}")
        object.__setattr__(self, "pass_through", pass_through)

        _choice("living_pieces", self.living_pieces, LIVING_PIECES)
        _choice("axis_frame", self.axis_frame, AXIS_FRAMES)
        _choice("infeasible_output", self.infeasible_output, INFEASIBLE_OUTPUTS)
        _finite_number("time_limit_s", self.time_limit_s, strictly_positive=True)
        _choice("area_source", self.area_source, AREA_SOURCES)
        _finite_number("clearance_m", self.clearance_m, 0)
        _finite_number("sliver_m2", self.sliver_m2, 0)

    def with_overrides(self, **overrides):
        known = {field.name for field in fields(self)}
        unknown = set(overrides) - known
        if unknown:
            raise ValueError(f"unknown settings: {sorted(unknown)}")
        return replace(self, **{key: value for key, value in overrides.items() if value is not None})

    def as_dict(self):
        return {field.name: getattr(self, field.name) for field in fields(self)}


DEFAULT = Settings()
