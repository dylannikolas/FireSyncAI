"""Sensor calendars: absent months/sensors remain unknown, never filled as zero."""
from __future__ import annotations

import pandas as pd

from firesync.core import aggregate_cells, monthly_activity

CALENDAR_COLUMNS = ["year", "month", "modis_cell_days", "viirs_cell_days", "observed_union_cell_days"]


def daily_sensor_activity(detections: pd.DataFrame, cell_m: int = 1000) -> pd.DataFrame:
    """Raw record and unique cell-day counts by sensor, no absent-day zeroes.

    Cell overlap here is same UTC day, NOT temporally aligned concordance.
    """
    cols = ["date", "modis_detections", "viirs_detections", "modis_cell_days", "viirs_cell_days",
            "observed_union_cell_days", "both_sensors_cell_days"]
    cells = aggregate_cells(detections, cell_m)
    if cells.empty:
        return pd.DataFrame(columns=cols)
    dates = cells.groupby("date", as_index=False).agg(observed_union_cell_days=("grid_x", "size"))
    both = cells.assign(both=cells.modis_seen & cells.viirs_seen).groupby("date", as_index=False).agg(both_sensors_cell_days=("both", "sum"))
    dates = dates.merge(both, on="date")
    for sensor, prefix in [("MODIS", "modis"), ("VIIRS", "viirs")]:
        subset = detections.loc[detections.sensor == sensor]
        raw = subset.groupby("date").size().rename(prefix+"_detections").reset_index()
        cell_counts = aggregate_cells(subset, cell_m).groupby("date").size().rename(prefix+"_cell_days").reset_index()
        dates = dates.merge(raw, on="date", how="left").merge(cell_counts, on="date", how="left")
    return dates.reindex(columns=cols).sort_values("date").reset_index(drop=True)


def sensor_calendar(detections: pd.DataFrame, cell_m: int = 1000) -> pd.DataFrame:
    if detections.empty:
        return pd.DataFrame(columns=CALENDAR_COLUMNS)
    union = monthly_activity(aggregate_cells(detections, cell_m)).rename(
        columns={"active_cell_days": "observed_union_cell_days"})
    result = union[["year", "month", "observed_union_cell_days"]]
    for sensor, column in (("MODIS", "modis_cell_days"), ("VIIRS", "viirs_cell_days")):
        counts = monthly_activity(aggregate_cells(detections.loc[detections.sensor == sensor], cell_m))
        counts = counts.rename(columns={"active_cell_days": column})
        result = result.merge(counts[["year", "month", column]], on=["year", "month"], how="left")
    return result.reindex(columns=CALENDAR_COLUMNS).sort_values(["year", "month"]).reset_index(drop=True)


def experimental_calendar(normalization: pd.DataFrame) -> pd.DataFrame:
    """Expose only held-out, supported cell-period estimates, never cell-days.

    The Phase 2 model estimates cell-period ratios. Applying its factor to full
    monthly cell-days would change the estimand and is intentionally forbidden.
    """
    cols = ["year", "month", "observed_modis", "observed_viirs", "reconciled_viirs",
            "reconciled_ci_low", "reconciled_ci_high"]
    if normalization.empty:
        return pd.DataFrame(columns=cols)
    supported = normalization.loc[normalization.reconciled_viirs.notna()].copy()
    return supported.rename(columns={"validation_year": "year"}).reindex(columns=cols).reset_index(drop=True)
