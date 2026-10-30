"""Pipeline parameters.

Defaults marked ASSUMPTION are placeholders to be justified from the data, not findings.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PipelineConfig:
    # Last date through which the data are complete. Drives right-censoring, so use the
    # date the sources are *complete* through (reporting lags make this earlier than the
    # download date), not the date you downloaded them.
    data_end: pd.Timestamp

    # Permits on one parcel whose issue dates chain with gaps <= this belong to one project.
    permit_chain_gap_days: int = 365  # ASSUMPTION

    # A permit may be issued up to this many days before the application is recorded.
    link_before_days: int = 0  # ASSUMPTION
    # Permit must be issued within this many days after the application.
    link_max_lag_days: int = 5 * 365  # ASSUMPTION

    # How unit counts combine across the permits of one project. "max" guards against
    # double-counting when every permit repeats the project's units; "sum" is right when
    # permits carry disjoint units. Check against the data before trusting either.
    unit_agg: str = "max"  # ASSUMPTION

    # Crude zoned-capacity conversion (floor area -> dwelling units).
    avg_unit_floor_area_m2: float = 75.0  # ASSUMPTION
    residential_efficiency: float = 0.8  # ASSUMPTION: share of floor area that is saleable/rentable

    def __post_init__(self):
        object.__setattr__(self, "data_end", pd.Timestamp(self.data_end))
        if self.unit_agg not in ("max", "sum"):
            raise ValueError("unit_agg must be 'max' or 'sum'")
        if self.permit_chain_gap_days < 0 or self.link_before_days < 0 or self.link_max_lag_days < 0:
            raise ValueError("day windows must be non-negative")
        if not 0 < self.residential_efficiency <= 1:
            raise ValueError("residential_efficiency must be in (0, 1]")
        if self.avg_unit_floor_area_m2 <= 0:
            raise ValueError("avg_unit_floor_area_m2 must be positive")
