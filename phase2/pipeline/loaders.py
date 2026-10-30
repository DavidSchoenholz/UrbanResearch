"""Map raw source tables onto the canonical schema.

No raw field names are filled in on purpose: take them from each dataset's verified data
dictionary (Phase 1 output), not from memory. Recode categorical values (for example
application outcomes) to the canonical vocabulary in schema.OUTCOMES before calling.
"""
from .schema import TABLES, validate


def mapping_template(table):
    """Return {canonical_column: None}; fill each value with the raw column name."""
    return {c: None for c in TABLES[table]["required"]}


def to_canonical(raw, mapping, table):
    required = set(TABLES[table]["required"])
    if set(mapping) != required:
        raise ValueError(f"{table}: mapping keys must be exactly {sorted(required)}")
    unset = sorted(k for k, v in mapping.items() if v is None)
    if unset:
        raise NotImplementedError(
            f"{table}: no raw column mapped for {unset}. Fill the mapping from the verified data dictionary.")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError(f"{table}: two canonical columns map to the same raw column")
    absent = sorted(v for v in mapping.values() if v not in raw.columns)
    if absent:
        raise KeyError(f"{table}: raw columns not found: {absent}")
    renamed = raw[list(mapping.values())].rename(columns={v: k for k, v in mapping.items()})
    return validate(renamed, table)
