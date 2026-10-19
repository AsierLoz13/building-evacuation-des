"""Monte Carlo replications, calibration against SimEvents and what-if experiments."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from . import config
from .model import Building, exit_summary, simulate

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "simevents"


# ---------------------------------------------------------------------------
# Original SimEvents results
# ---------------------------------------------------------------------------
def load_simevents(scenario: str) -> pd.DataFrame:
    """Exit times exported from the original SimEvents model (one replication, rng(42))."""
    return pd.read_csv(DATA_DIR / f"{scenario}.csv")


def simevents_summary(scenario: str) -> pd.DataFrame:
    df = load_simevents(scenario)
    g = df.groupby("exit")
    out = pd.DataFrame({"evacuated": g["cumulative_evacuated"].max(), "clearance_s": g["time_s"].max()})
    return out.reindex(config.EXITS)


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------
def monte_carlo(scenario: str, n_reps: int = 500, base_seed: int = 0,
                building: Building | None = None) -> dict:
    """Run ``n_reps`` independent replications (seeds base_seed .. base_seed + n_reps - 1).

    Returns
      ``runs``      one row per replication: t_max, people, clearance time per exit
      ``elements``  mean queue wait per element, averaged over replications
    """
    rows, el_rows = [], []
    for i in range(n_reps):
        res = simulate(scenario, seed=base_seed + i, building=building)
        ex = exit_summary(res["occupants"])
        row = {"rep": i, "t_max": res["t_max"], "people": len(res["occupants"])}
        row.update({f"clear_{e}": ex.loc[e, "clearance_s"] for e in config.EXITS})
        row.update({f"n_{e}": ex.loc[e, "evacuated"] for e in config.EXITS})
        rows.append(row)
        el = res["elements"].assign(rep=i)
        el_rows.append(el)
    runs = pd.DataFrame(rows)
    elements = (pd.concat(el_rows).groupby("element")[["served", "mean_wait", "max_wait"]]
                .mean().sort_values("mean_wait", ascending=False))
    return {"runs": runs, "elements": elements}


def summarize_tmax(runs: pd.DataFrame) -> pd.Series:
    t = runs["t_max"]
    return pd.Series({
        "mean": t.mean(), "std": t.std(), "p05": t.quantile(0.05),
        "median": t.median(), "p95": t.quantile(0.95), "max": t.max(),
    })


# ---------------------------------------------------------------------------
# Calibration of the undocumented geometry against SimEvents scenario E1
# ---------------------------------------------------------------------------
CALIBRATED = {
    # parameter name -> list of (element, field) it controls
    "door_length": [(e, "length") for e, v in config.ELEMENTS.items()
                    if v["kind"] == "flat" and v["capacity"] == 1],
    "landing_door_length": [("landing_door", "length")],
    "ext_stair_length": [(e, "length") for e in config.ELEMENTS if e.startswith("ext_stair")],
}


def building_with(params: dict, base: Building | None = None) -> Building:
    b = (base or Building()).copy()
    for name, value in params.items():
        for element, fld in CALIBRATED[name]:
            b.elements[element][fld] = float(value)
    return b


def calibration_loss(x, n_reps: int = 20, scenario: str = "E1") -> float:
    """RMSE (s) between mean simulated and SimEvents clearance time of every exit.

    Common random numbers (same seeds for every parameter vector) keep the
    objective smooth enough for Nelder-Mead.
    """
    params = dict(zip(CALIBRATED, x))
    if min(params.values()) <= 0:
        return 1e9
    target = simevents_summary(scenario)["clearance_s"]
    mc = monte_carlo(scenario, n_reps=n_reps, base_seed=10_000, building=building_with(params))
    sim = pd.Series({e: mc["runs"][f"clear_{e}"].mean() for e in config.EXITS})
    return float(np.sqrt(((sim - target) ** 2).mean()))


def calibrate(x0=(2.0, 2.0, 9.0), n_reps: int = 20) -> dict:
    res = minimize(calibration_loss, x0=np.asarray(x0), args=(n_reps,), method="Nelder-Mead",
                   options={"xatol": 0.01, "fatol": 0.1, "maxiter": 120})
    return {"params": dict(zip(CALIBRATED, res.x)), "rmse_s": float(res.fun), "result": res}


# ---------------------------------------------------------------------------
# Interventions proposed in the report (Section 8.2)
# ---------------------------------------------------------------------------
def reroute_p1_mediums(building: Building | None = None) -> Building:
    """Send the outer medium classrooms of P1 to the interior stair instead of the walkway."""
    b = (building or Building()).copy()
    for space in ("p1_med_1", "p1_med_4"):
        b.spaces[space]["route"] = "p1_landing"
    return b


def widen_external_stairs(extra_capacity: int = 3, building: Building | None = None,
                          only_ground_flight: bool = True) -> Building:
    """Add capacity (wider stairs) to the external stairs. By default only the P1 -> ground flight."""
    b = (building or Building()).copy()
    for name, el in b.elements.items():
        if name.startswith("ext_stair") and (not only_ground_flight or name.endswith("p1_ground")):
            el["capacity"] += extra_capacity
    return b
