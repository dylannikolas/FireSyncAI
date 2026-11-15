"""FIRMS detections: schema harmonization, common-area aggregation and exploratory seasonality.

Methodological scope: aggregation to equal-area cells is not cross-sensor
radiometric calibration; the derived unit is observed active cell-days, not fires.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pyproj import Transformer

_FORWARD = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
REQUIRED = {"latitude", "longitude", "acq_date", "acq_time"}


def normalize_firms(df: pd.DataFrame, sensor_hint: str | None = None) -> pd.DataFrame:
    """Parse MODIS/VIIRS CSV as UTC while preserving source and sensor-specific confidence."""
    if df.empty:
        return pd.DataFrame(columns=["latitude", "longitude", "acquired_utc", "date", "sensor", "satellite", "confidence", "frp", "version"])
    data = df.copy()
    data.columns = data.columns.astype(str).str.strip().str.lower()
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"Columnas FIRMS faltantes: {', '.join(sorted(missing))}")

    hint = (sensor_hint or "").upper()
    if "instrument" in data:
        inst = data["instrument"].fillna("").astype(str).str.upper().str.strip()
    else:
        inst = pd.Series("", index=data.index, dtype="str")
    sat = data.get("satellite", pd.Series("", index=data.index)).fillna("").astype(str).str.upper().str.strip()
    sensor = pd.Series("", index=data.index, dtype="str")
    sensor.loc[inst.str.contains("MODIS", regex=False) | sat.isin(["T", "A", "TERRA", "AQUA"])] = "MODIS"
    sensor.loc[inst.str.contains("VIIRS", regex=False) | sat.isin(["N", "N20", "N21", "SNPP", "SUOMI-NPP", "NOAA-20", "NOAA-21"])] = "VIIRS"
    if "MODIS" in hint or "VIIRS" in hint:
        sensor.loc[sensor == ""] = "MODIS" if "MODIS" in hint else "VIIRS"
    if (sensor == "").any():
        raise ValueError("No se puede identificar el sensor. Incluye 'instrument' o usa un nombre de archivo con MODIS/VIIRS.")

    dates = pd.to_datetime(data["acq_date"], errors="coerce", utc=True)
    times = data["acq_time"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(4)
    time_valid = times.str.fullmatch(r"\d{4}").fillna(False)
    hh = pd.to_numeric(times.str[:2], errors="coerce")
    mm = pd.to_numeric(times.str[2:], errors="coerce")
    valid_time = time_valid & hh.between(0, 23) & mm.between(0, 59)
    acquired = dates + pd.to_timedelta(hh.fillna(0), unit="h") + pd.to_timedelta(mm.fillna(0), unit="m")
    data["latitude"] = pd.to_numeric(data["latitude"], errors="coerce")
    data["longitude"] = pd.to_numeric(data["longitude"], errors="coerce")
    good = valid_time & dates.notna() & data["latitude"].between(-85.0, 85.0) & data["longitude"].between(-180, 180)
    # EPSG:6933 is defined for latitudes between ~86°S and ~86°N.
    out = pd.DataFrame({
        "latitude": data.loc[good, "latitude"].to_numpy(dtype=float),
        "longitude": data.loc[good, "longitude"].to_numpy(dtype=float),
        "acquired_utc": acquired.loc[good].to_numpy(),
        "sensor": sensor.loc[good].to_numpy(),
        "satellite": sat.loc[good].to_numpy(),
        "confidence": data.get("confidence", pd.Series("", index=data.index)).loc[good].astype(str).to_numpy(),
        "frp": pd.to_numeric(data.get("frp", pd.Series(np.nan, index=data.index)), errors="coerce").loc[good].to_numpy(),
        "version": data.get("version", pd.Series("", index=data.index)).loc[good].astype(str).to_numpy(),
    })
    if out.empty:
        raise ValueError("No quedaron observaciones con fecha, hora y coordenadas válidas.")
    out["acquired_utc"] = pd.to_datetime(out["acquired_utc"], utc=True)
    out["date"] = out["acquired_utc"].dt.date
    return out.drop_duplicates(subset=["latitude", "longitude", "acquired_utc", "sensor", "satellite"]).reset_index(drop=True)


def confidence_filter(detections: pd.DataFrame, modis_min: int = 0, exclude_viirs_low: bool = False) -> pd.DataFrame:
    """Optional sensitivity filter; MODIS (%) and VIIRS (l/n/h) MUST NOT be combined."""
    data = detections.copy()
    numeric = pd.to_numeric(data["confidence"], errors="coerce")
    modis_ok = (data["sensor"] != "MODIS") | (numeric >= modis_min) | (numeric.isna() & (modis_min == 0))
    viirs_ok = (data["sensor"] != "VIIRS") | (~data["confidence"].str.lower().isin(["l", "low"])) | (not exclude_viirs_low)
    return data.loc[modis_ok & viirs_ok].copy()


def aggregate_cells(detections: pd.DataFrame, cell_m: int = 1000) -> pd.DataFrame:
    """Unique 1 km² (or custom size) EPSG:6933 cells per UTC day.

    This reduces multiple satellite detections within the same cell and day,
    but does not assert one cell-day is one unique fire or an incident.
    """
    if cell_m < 375 or cell_m > 10000:
        raise ValueError("cell_m debe estar entre 375 y 10 000 m")
    cols = ["date", "grid_x", "grid_y", "latitude", "longitude", "raw_count", "modis_seen", "viirs_seen", "satellites", "max_frp"]
    if detections.empty:
        return pd.DataFrame(columns=cols)
    data = detections.copy()
    x, y = _FORWARD.transform(data["longitude"].to_numpy(), data["latitude"].to_numpy())
    data["grid_x"] = np.floor(np.array(x) / cell_m).astype("int64")
    data["grid_y"] = np.floor(np.array(y) / cell_m).astype("int64")
    # Representative observed point per cell-day; retains original geographic location.
    grouped = data.groupby(["date", "grid_x", "grid_y"], as_index=False).agg(
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        raw_count=("sensor", "size"),
        modis_seen=("sensor", lambda s: "MODIS" in set(s)),
        viirs_seen=("sensor", lambda s: "VIIRS" in set(s)),
        satellites=("satellite", lambda s: ", ".join(sorted(set(s) - {""}))),
        max_frp=("frp", "max"),
    )
    return grouped.sort_values(["date", "grid_x", "grid_y"]).reset_index(drop=True)


def daily_activity(cells: pd.DataFrame) -> pd.DataFrame:
    """Observations on detected days only; missing dates are NOT assumed fire-free."""
    if cells.empty:
        return pd.DataFrame(columns=["date", "active_cell_days", "raw_detections", "both_sensors"])
    return cells.groupby("date", as_index=False).agg(
        active_cell_days=("grid_x", "size"),
        raw_detections=("raw_count", "sum"),
        both_sensors=("modis_seen", lambda s: 0),
    ).drop(columns="both_sensors").merge(
        cells.assign(both_sensors=cells["modis_seen"] & cells["viirs_seen"]).groupby("date", as_index=False)["both_sensors"].sum(),
        on="date",
    )


def monthly_activity(cells: pd.DataFrame) -> pd.DataFrame:
    if cells.empty:
        return pd.DataFrame(columns=["year", "month", "active_cell_days", "raw_detections"])
    data = cells.copy()
    data["year"] = pd.to_datetime(data["date"]).dt.year
    data["month"] = pd.to_datetime(data["date"]).dt.month
    return data.groupby(["year", "month"], as_index=False).agg(
        active_cell_days=("grid_x", "size"), raw_detections=("raw_count", "sum")
    )


def historical_anomalies(monthly: pd.DataFrame, minimum_prior_years: int = 2) -> pd.DataFrame:
    """Descriptive month-vs-prior-years ratios for observed months only.

    Requires the analyst to confirm comparable historical spatial coverage and
    sensor acquisition/sampling conditions. Not a validated fire-risk forecast.
    """
    if monthly.empty:
        return pd.DataFrame(columns=["year", "month", "active_cell_days", "prior_mean", "ratio", "z_score", "n_prior"])
    rows = []
    monthly = monthly.sort_values(["year", "month"])
    for _, row in monthly.iterrows():
        prior = monthly.loc[(monthly["month"] == row["month"]) & (monthly["year"] < row["year"]), "active_cell_days"]
        mean = float(prior.mean()) if len(prior) >= minimum_prior_years else np.nan
        std = float(prior.std(ddof=1)) if len(prior) >= minimum_prior_years else np.nan
        ratio = (float(row["active_cell_days"]) / mean) if pd.notna(mean) and mean > 0 else np.nan
        z = (float(row["active_cell_days"]) - mean) / std if pd.notna(std) and std > 0 else np.nan
        rows.append({"year": int(row["year"]), "month": int(row["month"]),
                     "active_cell_days": int(row["active_cell_days"]), "prior_mean": mean,
                     "ratio": ratio, "z_score": z, "n_prior": int(len(prior))})
    return pd.DataFrame(rows)
