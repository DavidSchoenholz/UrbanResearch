"""Synthetic data with a known ground truth, for testing the pipeline end to end.

Nothing here describes Toronto; the numbers are arbitrary and exist only so estimators can be
checked against a truth. Each application gets a latent timeline (decision, permit, completion)
that is generated in full and then administratively censored at data_end.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SyntheticData:
    parcels: pd.DataFrame
    zoning_versions: pd.DataFrame
    applications: pd.DataFrame
    permits: pd.DataFrame
    truth: pd.DataFrame  # app_id, latent_complete_days, latent_competing_days (inf if never)
    data_end: pd.Timestamp


def _days(n):
    return pd.to_timedelta(np.asarray(n, dtype=float), unit="D")


def generate(n_parcels=20000, seed=0, data_end="2025-12-31", span_start="2012-01-01",
             p_application=0.35, p_asofright=0.05):
    rng = np.random.default_rng(seed)
    data_end = pd.Timestamp(data_end)
    start = pd.Timestamp(span_start)
    span_days = (data_end - start).days
    pid = np.arange(1, n_parcels + 1)

    lot = rng.lognormal(6.5, 0.5, n_parcels)
    fsi = rng.choice([0.6, 1.0, 2.0, 3.0], n_parcels, p=[0.4, 0.3, 0.2, 0.1])
    parcels = pd.DataFrame({
        "parcel_id": pid, "lot_area_m2": lot,
        "existing_floor_area_m2": fsi * lot * rng.uniform(0.3, 1.1, n_parcels),
    })

    changed = rng.random(n_parcels) < 0.3
    change_date = start + _days(rng.integers(0, span_days, n_parcels))
    base = pd.DataFrame({
        "parcel_id": pid, "zone_code": "R_old", "max_fsi": fsi, "max_height_m": 12.0,
        "effective_from": pd.Timestamp("1900-01-01"),
        "effective_to": pd.Series(change_date).where(changed),
    })
    upz = pd.DataFrame({
        "parcel_id": pid[changed], "zone_code": "R_new", "max_fsi": fsi[changed] * 2, "max_height_m": 24.0,
        "effective_from": change_date[changed], "effective_to": pd.NaT,
    })
    zoning = pd.concat([base, upz], ignore_index=True)

    # Applications and latent timelines.
    app_parcels = pid[rng.random(n_parcels) < p_application]
    n = len(app_parcels)
    submitted = start + _days(rng.integers(0, span_days + 1, n))
    decision_lag = rng.exponential(300, n)
    outcome_latent = rng.choice(["approved", "refused", "withdrawn"], n, p=[0.75, 0.15, 0.10])
    goes_to_permit = (outcome_latent == "approved") & (rng.random(n) < 0.8)
    permit_lag = rng.exponential(400, n)
    n_permits = rng.choice([1, 2, 3], n, p=[0.6, 0.3, 0.1])
    units = 1 + rng.poisson(20, n)

    permit_rows = []
    latent_complete = np.full(n, np.inf)
    for i in np.flatnonzero(goes_to_permit):
        offsets = np.concatenate([[0.0], rng.uniform(0, 120, n_permits[i] - 1)])
        construct = rng.lognormal(np.log(1000), 0.3, n_permits[i])
        issued_days = decision_lag[i] + permit_lag[i] + offsets
        latent_complete[i] = (issued_days + construct).max()
        for k in range(n_permits[i]):
            permit_rows.append((i, k, issued_days[k], construct[k]))
    latent_competing = np.where(outcome_latent != "approved", decision_lag, np.inf)

    decided = submitted + _days(decision_lag)
    decided_obs = pd.Series(decided).where(decided <= data_end)
    outcome_obs = np.where(decided_obs.notna(), outcome_latent, "pending")
    apps = pd.DataFrame({
        "app_id": np.arange(1, n + 1), "parcel_id": app_parcels, "submitted_date": submitted,
        "decided_date": decided_obs, "outcome": outcome_obs,
        "requires_rezoning": rng.random(n) < 0.5, "units_proposed": units,
    })

    # Permits of linked projects: every permit repeats the project's units (a double-counting
    # trap for unit_agg='sum'); units lost are recorded on the first permit only.
    lost = rng.poisson(1, n)
    rows = []
    for i, k, issued_days, construct in permit_rows:
        issued = submitted[i] + _days(issued_days)
        if issued > data_end:
            continue
        cleared = issued + _days(construct)
        rows.append((app_parcels[i], issued, cleared if cleared <= data_end else pd.NaT,
                     units[i], lost[i] if k == 0 else 0))

    # As-of-right projects: permits with no application at all.
    free = pid[(rng.random(n_parcels) < p_asofright) & ~np.isin(pid, app_parcels)]
    f_issued = start + _days(rng.integers(0, span_days, len(free)))
    f_constr = rng.lognormal(np.log(800), 0.3, len(free))
    for j in range(len(free)):
        cleared = f_issued[j] + _days(f_constr[j])
        rows.append((free[j], f_issued[j], cleared if cleared <= data_end else pd.NaT,
                     1 + rng.poisson(6), 0))

    permits = pd.DataFrame(rows, columns=["parcel_id", "issued_date", "cleared_date",
                                          "units_created", "units_lost"])
    permits.insert(0, "permit_id", np.arange(1, len(permits) + 1))

    truth = pd.DataFrame({
        "app_id": apps["app_id"], "latent_complete_days": latent_complete,
        "latent_competing_days": latent_competing,
    })
    return SyntheticData(parcels, zoning, apps, permits, truth, data_end)
