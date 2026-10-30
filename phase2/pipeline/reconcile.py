"""Compare project-level completions with an aggregate completions series (for example CMHC)."""


def reconcile_with_aggregate(projects, aggregate, year_col="year", count_col="completions"):
    """Yearly units from cleared projects vs an aggregate completions count.

    aggregate: DataFrame with year_col and count_col. Both series count dwelling units only if
    their definitions match (net vs gross, which building types), so a ratio far from 1 or
    drifting over time is a measurement-definition finding, not necessarily an error. This is
    city-wide; compare finer geographies only if the aggregate source provides them.
    """
    cleared = projects.dropna(subset=["cleared_date"])
    mine = (cleared.assign(year=cleared["cleared_date"].dt.year)
                   .groupby("year")
                   .agg(projects_cleared=("project_id", "count"), units_cleared=("net_units", "sum")))
    agg = aggregate.set_index(year_col)[[count_col]].rename(columns={count_col: "aggregate_completions"})
    out = mine.join(agg, how="outer")
    out["ratio_units_to_aggregate"] = out["units_cleared"] / out["aggregate_completions"]
    out.index.name = "year"
    return out.reset_index()
