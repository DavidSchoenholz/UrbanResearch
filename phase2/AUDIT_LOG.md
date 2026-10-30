# Audit log

## Audit 1: code review against failure modes
Fixed:
1. Refused/withdrawn applications with no decision date were silently censored, overstating
   completion. Now flagged (`competing_missing_date`) and reported by `run()`.
2. `requires_rezoning` given as strings silently made every route `unknown`, and a pandas
   nullable-boolean column would crash `np.select`. Now normalized to nullable boolean in
   `validate` (strings are rejected) and the route logic is NA-safe.
3. `run()` did not report a parcel match rate. Added `parcel_match_rate`.

## Audit 2: empirical checks
- pyflakes: removed unused imports.
- Tests pass from the repo root and from `phase2/`, with `-W error`, and on pandas 2.2.3 as well
  as the newest pandas (the geopandas test skips when geopandas is absent).
- Mutation checks (10 injected bugs in a scratch copy). Two survived at first and led to new
  tests: signed-vs-absolute lag in greedy linking (the old test used only positive lags), and the
  precedence of a completed project over a refusal in the missing-date flag. All 10 are now caught.

Not covered: the code has never touched real data, so field names, join keys and the realism of
every default in `config.py` are untested.
