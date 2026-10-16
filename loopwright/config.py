from dataclasses import dataclass, fields, replace
import math
<<<<<<< HEAD

=======
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4

# Values each setting accepts. A tuple lists only the readings the solver
# implements; add a value together with the code that handles it.
ZONE_LINKS = ("strict", "circulation", "through_rooms")
PASS_THROUGH = ("circulation", "bathroom", "stair", "other_zones")
INPUT_FORMATS = ("auto", "json", "resplan")
<<<<<<< HEAD
NODE_RULES = ("pole",)
HUB_MOUNTS = ("free",)
LIVING_PIECES = ("merge", "separate")
=======
NODE_RULES = ("near_doors", "pole")
HUB_MOUNTS = ("free",)
LIVING_PIECES = ("merge", "split")
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
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
<<<<<<< HEAD
=======
    # Q3, answered by the organisers' slide 7: turns at nodes and the hub are bends; crossings
    # and overlap count inside and between rings; within 1 mm is the same point or line
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
    bend_at_node: bool = True
    tolerance_m: float = 0.001
    count_self_crossings: bool = True
    max_nodes: int = 5
    max_area_m2: float = 100.0
    input_format: str = "auto"
    node_rule: str = "near_doors"
    # Q6, answered in the Eval-01 meeting: a node keeps this far from its room's walls
    node_wall_m: float = 0.5
    hub_mount: str = "free"
    # Q7, Eval-01 meeting: a hub may not sit on a node ("0 cannot be the case"); we keep it this far
    min_hub_node_m: float = 0.5
    pass_through: tuple = ("circulation", "bathroom", "stair", "other_zones")
    living_pieces: str = "merge"
    axis_frame: str = "drawing"
    infeasible_output: str = "flag_and_relaxed"
    time_limit_s: float = 10.0
    area_source: str = "polygon"
<<<<<<< HEAD
=======
    # Q17, Eval-01 meeting: eligible rooms under this area get no node (rooms too narrow
    # for a node node_wall_m from the walls get none either)
    min_room_m2: float = 2.0
    # Solver option (not a rule reading): re-route legs so they take a separate lane rather than
    # run on top of cable already placed, when that lowers J
    separate_lanes: bool = True
    # Geometry constants (not rule readings)
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
    clearance_m: float = 0.10
    sliver_m2: float = 0.5

    def __post_init__(self):
        _choice("zone_link", self.zone_link, ZONE_LINKS)
        _finite_number("bend_m", self.bend_m, 0)
        _finite_number("crossing_m", self.crossing_m, 0)
        _finite_number("overlap_factor", self.overlap_factor, 0)
        _boolean("bend_at_node", self.bend_at_node)
<<<<<<< HEAD
        _finite_number("lane_gap_m", self.lane_gap_m, 0)
=======
        _finite_number("tolerance_m", self.tolerance_m, 0)
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
        _boolean("count_self_crossings", self.count_self_crossings)
        if type(self.max_nodes) is not int or self.max_nodes < 1:
            raise ValueError("max_nodes must be a positive integer")
        _finite_number("max_area_m2", self.max_area_m2, strictly_positive=True)
        _choice("input_format", self.input_format, INPUT_FORMATS)
        _choice("node_rule", self.node_rule, NODE_RULES)
<<<<<<< HEAD
        _choice("hub_mount", self.hub_mount, HUB_MOUNTS)
        _finite_number("min_hub_node_m", self.min_hub_node_m, 0)
=======
        _finite_number("node_wall_m", self.node_wall_m, 0)
        _finite_number("min_room_m2", self.min_room_m2, 0)
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
        _boolean("separate_lanes", self.separate_lanes)
        _finite_number("clearance_m", self.clearance_m, 0)
        _finite_number("sliver_m2", self.sliver_m2, 0)
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4

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
