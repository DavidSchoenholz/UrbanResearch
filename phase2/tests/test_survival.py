import numpy as np
import pytest

from pipeline.survival import (bootstrap_cif, cif_at, cumulative_incidence, kaplan_meier,
                               time_to_share)


def test_cif_hand_computed_with_competing_risk():
    # times 1,2,3,4; events: cause1, cause2, censored, cause1
    cif = cumulative_incidence([1, 2, 3, 4], [1, 2, 0, 1], cause=1)
    assert np.allclose(cif["time"], [0, 1, 2, 4])
    assert np.allclose(cif["cif"], [0, 0.25, 0.25, 0.75])
    other = cumulative_incidence([1, 2, 3, 4], [1, 2, 0, 1], cause=2)
    assert np.isclose(other["cif"].iloc[-1], 0.25)
    # causes plus "no event yet" must account for everyone (here nobody remains at the end)
    assert np.isclose(cif["cif"].iloc[-1] + other["cif"].iloc[-1], 1.0)


def test_cif_without_competing_matches_one_minus_km():
    d = [1, 2, 3, 4, 5, 6]
    e = [1, 0, 1, 1, 0, 1]
    cif = cumulative_incidence(d, e)
    km = kaplan_meier(d, np.array(e) == 1)
    assert np.allclose(cif["cif"].to_numpy(), 1 - km["survival"].to_numpy())


def test_treating_competing_as_censored_overstates_incidence():
    d = [1, 2, 3, 4]
    e = [2, 2, 1, 1]
    true_cif = cumulative_incidence(d, e, cause=1)["cif"].iloc[-1]
    naive = 1 - kaplan_meier(d, np.array(e) == 1)["survival"].iloc[-1]
    assert naive > true_cif


def test_ties_events_before_censoring():
    cif = cumulative_incidence([2, 2, 2], [1, 0, 0])
    assert np.isclose(cif["cif"].iloc[-1], 1 / 3)


def test_no_events_gives_flat_zero():
    cif = cumulative_incidence([1, 2, 3], [0, 0, 0])
    assert (cif["cif"] == 0).all()


def test_step_lookup_and_time_to_share():
    cif = cumulative_incidence([1, 2, 3, 4], [1, 2, 0, 1])
    assert np.allclose(cif_at(cif, [0, 0.5, 1, 1.9, 2, 10]), [0, 0, 0.25, 0.25, 0.25, 0.75])
    assert time_to_share(cif, 0.5) == 4
    assert np.isnan(time_to_share(cif, 0.9))


def test_input_validation():
    with pytest.raises(ValueError):
        cumulative_incidence([], [])
    with pytest.raises(ValueError):
        cumulative_incidence([-1, 2], [1, 0])
    with pytest.raises(ValueError):
        cumulative_incidence([1, 2], [1])


def test_bootstrap_interval_is_ordered_and_covers_estimate():
    rng = np.random.default_rng(0)
    d = rng.exponential(10, 500)
    e = (rng.random(500) < 0.7).astype(int)
    out = bootstrap_cif(d, e, grid=[5, 10, 20], n_boot=100, seed=1)
    assert (out["lo"] <= out["hi"]).all()
    assert ((out["lo"] <= out["estimate"]) & (out["estimate"] <= out["hi"])).all()
