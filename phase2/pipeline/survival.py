"""Time-to-event estimators that respect right-censoring and competing outcomes.

Naive completion rates for recent application cohorts are biased downward because many
have not had time to complete. The Aalen-Johansen cumulative incidence below uses every
application for as long as it is observed, and treats refusal/withdrawal as a competing
outcome rather than as censoring (treating it as censoring overstates completion).

Assumption: censoring is independent of the outcome (administrative censoring at the data
cutoff satisfies this if the process is stable over calendar time; a policy change or market
cycle that alters timelines across cohorts violates it, so compare cohorts, not only pooled).
"""
import numpy as np
import pandas as pd


def _check(durations, events):
    d = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    if d.size == 0 or d.shape != e.shape:
        raise ValueError("durations and events must be non-empty and the same length")
    if np.isnan(d).any() or (d < 0).any():
        raise ValueError("durations must be non-negative and non-null")
    order = np.argsort(d, kind="stable")
    return d[order], e[order]


def cumulative_incidence(durations, events, cause=1):
    """Aalen-Johansen cumulative incidence of `cause`.

    events: 0 = censored, 1.. = event codes (cause is the one of interest, the rest compete).
    Returns time, n_at_risk, n_cause, n_other, cif, starting from a row at time 0.
    Events at a time are processed before censorings at the same time.
    """
    d, e = _check(durations, events)
    n = d.size
    ev = e > 0
    if not ev.any():
        return pd.DataFrame({"time": [0.0], "n_at_risk": [n], "n_cause": [0], "n_other": [0], "cif": [0.0]})

    times, inv = np.unique(d[ev], return_inverse=True)
    d_all = np.bincount(inv).astype(float)
    d_cause = np.bincount(inv, weights=(e[ev] == cause).astype(float))
    at_risk = (n - np.searchsorted(d, times, side="left")).astype(float)

    surv_before = np.concatenate([[1.0], np.cumprod(1.0 - d_all / at_risk)[:-1]])
    cif = np.cumsum(surv_before * d_cause / at_risk)
    return pd.DataFrame({
        "time": np.concatenate([[0.0], times]),
        "n_at_risk": np.concatenate([[n], at_risk.astype(int)]),
        "n_cause": np.concatenate([[0], d_cause.astype(int)]),
        "n_other": np.concatenate([[0], (d_all - d_cause).astype(int)]),
        "cif": np.concatenate([[0.0], cif]),
    })


def kaplan_meier(durations, observed):
    """Kaplan-Meier survival where observed (bool) marks the event; all else is censored.

    Use only when there are no competing outcomes; otherwise use cumulative_incidence.
    """
    d, e = _check(durations, np.asarray(observed, dtype=int))
    n = d.size
    ev = e > 0
    if not ev.any():
        return pd.DataFrame({"time": [0.0], "n_at_risk": [n], "n_events": [0], "survival": [1.0]})
    times, inv = np.unique(d[ev], return_inverse=True)
    d_ev = np.bincount(inv).astype(float)
    at_risk = (n - np.searchsorted(d, times, side="left")).astype(float)
    surv = np.cumprod(1.0 - d_ev / at_risk)
    return pd.DataFrame({
        "time": np.concatenate([[0.0], times]),
        "n_at_risk": np.concatenate([[n], at_risk.astype(int)]),
        "n_events": np.concatenate([[0], d_ev.astype(int)]),
        "survival": np.concatenate([[1.0], surv]),
    })


def step_value(curve, value_col, t):
    """Evaluate a right-continuous step curve (time column, value_col) at times t."""
    times = curve["time"].to_numpy()
    idx = np.searchsorted(times, np.asarray(t, dtype=float), side="right") - 1
    return curve[value_col].to_numpy()[np.clip(idx, 0, None)]


def cif_at(cif_df, t):
    return step_value(cif_df, "cif", t)


def time_to_share(cif_df, q):
    """First time the cumulative incidence reaches q, or NaN if it never does (a plateau
    below q is a finding, not missing data)."""
    hit = cif_df.loc[cif_df["cif"] >= q, "time"]
    return float(hit.iloc[0]) if len(hit) else float("nan")


def bootstrap_cif(durations, events, grid, cause=1, n_boot=200, alpha=0.05, seed=0):
    """Percentile bootstrap CI of the cumulative incidence at the times in `grid`.

    Resamples applications independently, so it ignores spatial clustering; treat the
    intervals as optimistic when parcels or wards share conditions.
    """
    d = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    grid = np.asarray(grid, dtype=float)
    rng = np.random.default_rng(seed)
    est = cif_at(cumulative_incidence(d, e, cause), grid)
    draws = np.empty((n_boot, grid.size))
    for b in range(n_boot):
        idx = rng.integers(0, d.size, d.size)
        draws[b] = cif_at(cumulative_incidence(d[idx], e[idx], cause), grid)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2], axis=0)
    return pd.DataFrame({"t": grid, "estimate": est, "lo": lo, "hi": hi})
