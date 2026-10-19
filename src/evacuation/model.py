"""Discrete-event simulation of a building evacuation as a network of FIFO queues.

Every occupant is a SimPy process:

1. waits its pre-movement time t_pre (alarm -> starts moving),
2. walks to the first element of its route,
3. for each element on the route, queues (FIFO) for one of the element's
   ``capacity`` slots and occupies it for ``length / (v * f)`` seconds, where
   f = alpha on stairs and 1 on flat elements (report, Eq. 6.1),
4. leaves the building at the last element of the route.

This mirrors the SimEvents model of the original project
(Entity Generator -> Entity Queue -> Entity Server -> Entity Terminator).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import simpy

from . import config


@dataclass
class Building:
    """All model inputs. Defaults come from ``config``; any field can be overridden."""

    elements: dict = field(default_factory=lambda: copy.deepcopy(config.ELEMENTS))
    routes: dict = field(default_factory=lambda: copy.deepcopy(config.ROUTES))
    spaces: dict = field(default_factory=lambda: copy.deepcopy(config.SPACES))
    profiles: dict = field(default_factory=lambda: copy.deepcopy(config.PROFILES))
    profile_mix: dict = field(default_factory=lambda: dict(config.PROFILE_MIX))
    scenarios: dict = field(default_factory=lambda: copy.deepcopy(config.SCENARIOS))

    def copy(self) -> "Building":
        return copy.deepcopy(self)


def _draw_count(spec, rng: np.random.Generator) -> int:
    if isinstance(spec, tuple) and spec[0] == "U":
        return int(rng.integers(spec[1], spec[2] + 1))
    return int(spec)


def _draw_route(spec, rng: np.random.Generator) -> str:
    if isinstance(spec, str):
        return spec
    names, probs = zip(*spec.items())
    return names[rng.choice(len(names), p=np.asarray(probs) / sum(probs))]


def simulate(scenario: str, seed: int = 0, building: Building | None = None) -> dict:
    """Run one replication of ``scenario``.

    Returns a dict with
      ``occupants``  one row per occupant (space, profile, exit, t_pre, t_exit, total wait)
      ``elements``   one row per element (people served, mean and max queue wait)
      ``t_max``      total evacuation time (last occupant out), seconds
    """
    b = building or Building()
    rng = np.random.default_rng(seed)
    env = simpy.Environment()
    resources = {name: simpy.Resource(env, capacity=e["capacity"]) for name, e in b.elements.items()}
    waits: dict[str, list[float]] = {name: [] for name in b.elements}
    records: list[dict] = []

    profile_names = list(b.profile_mix)
    profile_p = np.array([b.profile_mix[p] for p in profile_names])
    profile_p = profile_p / profile_p.sum()

    def occupant(space: str, route: str, profile: str, t_pre: float):
        prof = b.profiles[profile]
        v, alpha = prof["speed"], prof["alpha"]
        yield env.timeout(t_pre)
        yield env.timeout(b.spaces[space]["walk"] / v)
        total_wait = 0.0
        for kind, value in b.routes[route]["steps"]:
            if kind == "walk":
                yield env.timeout(value / v)
                continue
            el = b.elements[value]
            factor = alpha if el["kind"] == "stair" else 1.0
            with resources[value].request() as req:
                t_arrive = env.now
                yield req
                w = env.now - t_arrive
                waits[value].append(w)
                total_wait += w
                yield env.timeout(el["length"] / (v * factor))
        records.append({
            "space": space, "profile": profile, "route": route,
            "exit": b.routes[route]["exit"], "t_pre": t_pre,
            "t_exit": env.now, "total_wait": total_wait,
        })

    occupancy = b.scenarios[scenario]["occupancy"]
    for space, spec in occupancy.items():
        n = _draw_count(spec, rng)
        for _ in range(n):
            profile = profile_names[rng.choice(len(profile_names), p=profile_p)]
            a, c = b.profiles[profile]["pre"]
            t_pre = rng.uniform(a, c)
            route = _draw_route(b.spaces[space]["route"], rng)
            env.process(occupant(space, route, profile, t_pre))

    env.run()

    occupants = pd.DataFrame(records)
    elements = pd.DataFrame([
        {"element": name, "served": len(w),
         "mean_wait": float(np.mean(w)) if w else 0.0,
         "max_wait": float(np.max(w)) if w else 0.0}
        for name, w in waits.items()
    ])
    t_max = float(occupants["t_exit"].max()) if len(occupants) else 0.0
    return {"occupants": occupants, "elements": elements, "t_max": t_max}


def exit_summary(occupants: pd.DataFrame) -> pd.DataFrame:
    """People evacuated and clearance time (last person out) for every exit."""
    g = occupants.groupby("exit")["t_exit"]
    out = pd.DataFrame({"evacuated": g.size(), "clearance_s": g.max()})
    return out.reindex(config.EXITS).fillna({"evacuated": 0})


def cumulative_curve(occupants: pd.DataFrame, exit_name: str) -> tuple[np.ndarray, np.ndarray]:
    """Step curve N_j(t): cumulative number of people out through ``exit_name``."""
    t = np.sort(occupants.loc[occupants["exit"] == exit_name, "t_exit"].to_numpy())
    return t, np.arange(1, len(t) + 1)
