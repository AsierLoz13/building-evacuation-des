"""Model inputs for the evacuation of Building G (Universidad Francisco de Vitoria).

Sources
-------
* Occupant profiles, profile mix and occupancy scenarios: project report (Tables 5.1-5.3).
* Building layout and evacuation routes: project report (Section 5.1), cross-checked
  against the per-exit counts exported from the original SimEvents model.
* Element lengths and capacities are NOT documented in the report. Values marked
  ``calibrated`` are fitted to the SimEvents output of scenario E1
  (see ``evacuation.calibration``); values marked ``assumed`` are engineering guesses.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Occupant profiles (report, Table 5.1)
#   speed     horizontal walking speed v_k (m/s)
#   alpha     stair speed reduction factor, 0 < alpha <= 1
#   pre       pre-movement time ~ U(a, b) seconds
# ---------------------------------------------------------------------------
PROFILES = {
    "young_male":   {"speed": 1.35, "alpha": 0.70, "pre": (15, 30)},
    "young_female": {"speed": 1.15, "alpha": 0.65, "pre": (15, 30)},
    "adult_male":   {"speed": 1.25, "alpha": 0.65, "pre": (20, 40)},
    "adult_female": {"speed": 1.05, "alpha": 0.60, "pre": (20, 40)},
    "senior":       {"speed": 0.80, "alpha": 0.50, "pre": (30, 60)},
}
# Profile mix assumed in every scenario (report, Figure 5.9)
PROFILE_MIX = {
    "young_male": 0.40, "young_female": 0.40,
    "adult_male": 0.08, "adult_female": 0.08, "senior": 0.04,
}

# ---------------------------------------------------------------------------
# Building elements = servers of the queueing network.
#   kind      "flat" (door, corridor) or "stair" (speed multiplied by alpha)
#   length    traversal length in metres -> service time = length / (v * f)
#   capacity  number of people that can traverse the element simultaneously
# Throughput of an element ~ capacity * speed / length (people per second).
# ---------------------------------------------------------------------------
DOOR_LENGTH = 1.98          # calibrated: single doorway incl. threshold/vestibule
LANDING_DOOR_LENGTH = 2.11  # calibrated: landing exit (double door, capacity 2)
EXT_STAIR_LENGTH = 8.64     # calibrated: external steel stairs (capacity 5)
INT_STAIR_LENGTH = 8.0      # assumed: one interior flight
P2_CORRIDOR_LENGTH = 15.0   # assumed

ELEMENTS = {
    # Basement (P-1)
    "pm1_exit_left":             {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "pm1_exit_right":            {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "pm1_stair_to_landing":      {"kind": "stair", "length": INT_STAIR_LENGTH, "capacity": 10},
    # Interior stair P1 -> P0 -> landing between P0 and P-1
    "p1_stair_to_p0":            {"kind": "stair", "length": INT_STAIR_LENGTH, "capacity": 10},
    "p0_stair_to_landing":       {"kind": "stair", "length": INT_STAIR_LENGTH / 2, "capacity": 10},
    "landing_door":              {"kind": "flat",  "length": LANDING_DOOR_LENGTH, "capacity": 2},
    # Ground floor (P0): each exit = two doors in series
    "p0_left_door_inner":        {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p0_left_door_outer":        {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p0_center_door_inner":      {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p0_center_door_outer":      {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p0_right_door_inner":       {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p0_right_door_outer":       {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    # First floor (P1): doors to the external walkway and stairs to the ground
    "p1_door_left":              {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p1_door_right":             {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "ext_stair_left_p1_ground":  {"kind": "stair", "length": EXT_STAIR_LENGTH, "capacity": 5},
    "ext_stair_right_p1_ground": {"kind": "stair", "length": EXT_STAIR_LENGTH, "capacity": 5},
    # Second floor (P2): shared corridor (capacity 6, report Section 6.2), doors and stairs to P1
    "p2_corridor_left":          {"kind": "flat",  "length": P2_CORRIDOR_LENGTH, "capacity": 6},
    "p2_door_left":              {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "p2_door_right":             {"kind": "flat",  "length": DOOR_LENGTH, "capacity": 1},
    "ext_stair_left_p2_p1":      {"kind": "stair", "length": EXT_STAIR_LENGTH, "capacity": 5},
    "ext_stair_right_p2_p1":     {"kind": "stair", "length": EXT_STAIR_LENGTH, "capacity": 5},
}

# ---------------------------------------------------------------------------
# Routes: ordered steps, either ("walk", metres) or ("el", element name).
# The last element of a route is the building exit reported in the results.
# Walking distances between elements are assumed.
# ---------------------------------------------------------------------------
ROUTES = {
    "pm1_left":   {"exit": "pm1_left",  "steps": [("el", "pm1_exit_left")]},
    "pm1_right":  {"exit": "pm1_right", "steps": [("el", "pm1_exit_right")]},
    "pm1_landing": {"exit": "landing", "steps": [
        ("el", "pm1_stair_to_landing"), ("walk", 2), ("el", "landing_door")]},
    "p1_landing": {"exit": "landing", "steps": [
        ("el", "p1_stair_to_p0"), ("walk", 3), ("el", "p0_stair_to_landing"),
        ("walk", 2), ("el", "landing_door")]},
    "p0_left":   {"exit": "p0_left", "steps": [
        ("el", "p0_left_door_inner"), ("walk", 2), ("el", "p0_left_door_outer")]},
    "p0_center": {"exit": "p0_center", "steps": [
        ("el", "p0_center_door_inner"), ("walk", 2), ("el", "p0_center_door_outer")]},
    "p0_right":  {"exit": "p0_right", "steps": [
        ("el", "p0_right_door_inner"), ("walk", 2), ("el", "p0_right_door_outer")]},
    "p1_ext_left":  {"exit": "stair_ext_left", "steps": [
        ("el", "p1_door_left"), ("walk", 6), ("el", "ext_stair_left_p1_ground")]},
    "p1_ext_right": {"exit": "stair_ext_right", "steps": [
        ("el", "p1_door_right"), ("walk", 6), ("el", "ext_stair_right_p1_ground")]},
    "p1_walkway_left":  {"exit": "stair_ext_left",  "steps": [("el", "ext_stair_left_p1_ground")]},
    "p1_walkway_right": {"exit": "stair_ext_right", "steps": [("el", "ext_stair_right_p1_ground")]},
    "p2_ext_left": {"exit": "stair_ext_left", "steps": [
        ("el", "p2_corridor_left"), ("el", "p2_door_left"), ("walk", 4),
        ("el", "ext_stair_left_p2_p1"), ("walk", 6), ("el", "ext_stair_left_p1_ground")]},
    "p2_ext_right": {"exit": "stair_ext_right", "steps": [
        ("el", "p2_door_right"), ("walk", 4),
        ("el", "ext_stair_right_p2_p1"), ("walk", 6), ("el", "ext_stair_right_p1_ground")]},
    "p2_walkway_left": {"exit": "stair_ext_left", "steps": [
        ("el", "ext_stair_left_p2_p1"), ("walk", 6), ("el", "ext_stair_left_p1_ground")]},
    "p2_walkway_right": {"exit": "stair_ext_right", "steps": [
        ("el", "ext_stair_right_p2_p1"), ("walk", 6), ("el", "ext_stair_right_p1_ground")]},
}

# ---------------------------------------------------------------------------
# Spaces (sources of occupants).
#   route   name in ROUTES, or a dict {route: probability} for open spaces
#           (walkway tables) whose occupants join the nearest flow
#   walk    distance (m) from the space to the first element of its route (assumed)
# ---------------------------------------------------------------------------
HALF_SPLIT = 0.5
SPACES = {
    # P-1: left classrooms -> Exit 1, right classrooms -> Exit 2,
    #      labs and corridor study tables -> interior stair -> landing exit
    "pm1_classroom_L50": {"route": "pm1_left",  "walk": 20},
    "pm1_classroom_L40": {"route": "pm1_left",  "walk": 12},
    "pm1_classroom_R40": {"route": "pm1_right", "walk": 12},
    "pm1_classroom_R50": {"route": "pm1_right", "walk": 20},
    "pm1_lab_20a":       {"route": "pm1_landing", "walk": 18},
    "pm1_lab_10":        {"route": "pm1_landing", "walk": 10},
    "pm1_lab_15":        {"route": "pm1_landing", "walk": 10},
    "pm1_lab_20b":       {"route": "pm1_landing", "walk": 18},
    "pm1_corridor":      {"route": "pm1_landing", "walk": 8},
    # P0: (big + medium) -> left exit, two central mediums -> centre, (medium + big) -> right
    "p0_big_L":  {"route": "p0_left",   "walk": 20},
    "p0_med_1":  {"route": "p0_left",   "walk": 12},
    "p0_med_2":  {"route": "p0_center", "walk": 12},
    "p0_med_3":  {"route": "p0_center", "walk": 12},
    "p0_med_4":  {"route": "p0_right",  "walk": 12},
    "p0_big_R":  {"route": "p0_right",  "walk": 20},
    # P1: outer rooms -> external walkway; two central mediums -> interior stair -> landing
    "p1_big_L":  {"route": "p1_ext_left",  "walk": 20},
    "p1_med_1":  {"route": "p1_ext_left",  "walk": 12},
    "p1_med_2":  {"route": "p1_landing",   "walk": 10},
    "p1_med_3":  {"route": "p1_landing",   "walk": 10},
    "p1_med_4":  {"route": "p1_ext_right", "walk": 12},
    "p1_big_R":  {"route": "p1_ext_right", "walk": 20},
    "p1_walkway": {"route": {"p1_walkway_left": HALF_SPLIT, "p1_walkway_right": HALF_SPLIT}, "walk": 3},
    # P2: classroom + mentoring room share a corridor to the left door; staff rooms -> right door
    "p2_classroom":  {"route": "p2_ext_left",  "walk": 15},
    "p2_mentoring":  {"route": "p2_ext_left",  "walk": 8},
    "p2_staff":      {"route": "p2_ext_right", "walk": 10},
    "p2_walkway": {"route": {"p2_walkway_left": HALF_SPLIT, "p2_walkway_right": HALF_SPLIT}, "walk": 3},
}

# ---------------------------------------------------------------------------
# Occupancy per scenario (report, Tables 5.2-5.3). An int is a fixed head count;
# ("U", a, b) is a discrete uniform draw on {a, ..., b}. Spaces not listed are empty.
# Where the report only gives "n rooms occupied", the specific rooms are those
# consistent with the per-exit counts of the SimEvents export.
# ---------------------------------------------------------------------------
SCENARIOS = {
    "E1": {  # peak hours, 100 %
        "label": "Peak hours (100 %)",
        "occupancy": {
            "pm1_classroom_L50": 50, "pm1_classroom_L40": 40, "pm1_classroom_R40": 40,
            "pm1_classroom_R50": 50, "pm1_lab_20a": 20, "pm1_lab_10": 10, "pm1_lab_15": 15,
            "pm1_lab_20b": 20, "pm1_corridor": ("U", 30, 40),
            "p0_big_L": 48, "p0_med_1": 30, "p0_med_2": 30, "p0_med_3": 30, "p0_med_4": 30, "p0_big_R": 48,
            "p1_big_L": 48, "p1_med_1": 30, "p1_med_2": 30, "p1_med_3": 30, "p1_med_4": 30, "p1_big_R": 48,
            "p1_walkway": ("U", 8, 16),
            "p2_classroom": 48, "p2_mentoring": ("U", 5, 20), "p2_staff": ("U", 10, 35),
            "p2_walkway": ("U", 5, 16),
        },
    },
    "E2": {  # afternoon, 75 %
        "label": "Afternoon (75 %)",
        "occupancy": {
            "pm1_classroom_L50": 50, "pm1_classroom_L40": 40, "pm1_classroom_R50": 50,
            "pm1_lab_20a": 20, "pm1_lab_20b": 20, "pm1_corridor": ("U", 12, 20),
            "p0_big_L": 48, "p0_med_1": 30, "p0_med_2": 30, "p0_med_3": 30, "p0_big_R": 48,
            "p1_big_L": 48, "p1_med_1": 30, "p1_med_2": 30, "p1_med_3": 30, "p1_big_R": 48,
            "p1_walkway": ("U", 2, 7),
            "p2_classroom": 48, "p2_mentoring": ("U", 2, 8), "p2_staff": ("U", 5, 15),
            "p2_walkway": ("U", 2, 7),
        },
    },
    "E3": {  # evening, 50 %
        "label": "Evening (50 %)",
        "occupancy": {
            "pm1_classroom_L50": 50, "pm1_classroom_R40": 40,
            "pm1_lab_20a": 8, "pm1_lab_20b": 7, "pm1_corridor": ("U", 5, 12),
            "p0_big_L": 48, "p0_med_1": 30, "p0_med_4": 30,
            "p1_big_L": 48, "p1_med_1": 30, "p1_med_4": 30,
            "p1_walkway": ("U", 1, 5),
            "p2_classroom": 20, "p2_mentoring": ("U", 0, 3), "p2_staff": ("U", 1, 5),
        },
    },
    "E4": {  # outside teaching hours, 25 %
        "label": "Off-hours (25 %)",
        "occupancy": {
            "pm1_classroom_L50": 50, "pm1_corridor": ("U", 0, 5),
            "p0_big_L": 48, "p0_big_R": 48,
            "p1_big_L": 48, "p1_big_R": 48, "p1_walkway": ("U", 0, 3),
            "p2_classroom": 20, "p2_staff": ("U", 1, 3),
        },
    },
}

EXITS = ["pm1_left", "pm1_right", "landing", "p0_left", "p0_center", "p0_right",
         "stair_ext_left", "stair_ext_right"]
EXIT_LABELS = {
    "pm1_left": "P-1 left door", "pm1_right": "P-1 right door", "landing": "Landing door",
    "p0_left": "P0 left door", "p0_center": "P0 centre door", "p0_right": "P0 right door",
    "stair_ext_left": "External stair (left)", "stair_ext_right": "External stair (right)",
}
