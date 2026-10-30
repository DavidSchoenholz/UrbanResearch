from pipeline import synthetic
from pipeline.config import PipelineConfig
from pipeline.survival import cif_at
from run_pilot import run


def _run(n_parcels, seed, **cfg_kw):
    data = synthetic.generate(n_parcels=n_parcels, seed=seed)
    cfg = PipelineConfig(data_end=data.data_end, **cfg_kw)
    return data, run(data.parcels, data.zoning_versions, data.applications, data.permits, cfg)


def test_pipeline_runs_and_links_cleanly():
    data, res = _run(4000, seed=3)
    d = res["link_diagnostics"]
    assert d["n_links"] > 0
    assert res["n_invalid_durations"] == 0
    assert res["zoning_match_rate"] == 1.0                     # baseline version starts in 1900
    assert not res["zoning_history"]["looks_like_single_snapshot"]
    # every linked project's application is on the same parcel by construction
    t = res["table"]
    assert t["stage_reached"].isin(["submitted", "approved", "permitted", "completed"]).all()
    assert not t["permit_without_approval"].any()


def test_unit_agg_sum_overcounts_projects():
    data = synthetic.generate(n_parcels=4000, seed=3)
    from pipeline.linking import aggregate_permits_to_projects
    from pipeline.schema import validate
    p = validate(data.permits, "permits")
    cfg_max = PipelineConfig(data_end=data.data_end, unit_agg="max")
    cfg_sum = PipelineConfig(data_end=data.data_end, unit_agg="sum")
    assert aggregate_permits_to_projects(p, cfg_sum)["units_created"].sum() > \
        aggregate_permits_to_projects(p, cfg_max)["units_created"].sum()


def test_cif_recovers_truth_and_naive_share_is_biased():
    data, res = _run(40000, seed=1)
    truth = data.truth
    for years in (3, 5, 8):
        days = years * 365.25
        t = float((truth["latent_complete_days"] <= days).mean())
        e = float(cif_at(res["cif"], [days])[0])
        assert abs(t - e) < 0.025, (years, t, e)
    naive = float((res["table"]["stage_reached"] == "completed").mean())
    truth_long = float((truth["latent_complete_days"] <= 10 * 365.25).mean())
    assert naive < truth_long - 0.05
