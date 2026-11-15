"""Conditional overlap diagnostics; no coverage, truth labels or FRP calibration.

Acquisition timestamps are detection-derived proxies, not verified overpasses.
Only paired timestamps enter diagnostics. Missing detections never imply a
cloud-free, fire-free observation. All normalization is experimental.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
import numpy as np
import pandas as pd

from firesync.core import _FORWARD


@dataclass
class CalibrationResult:
    periods: pd.DataFrame
    monthly: pd.DataFrame
    normalization: pd.DataFrame
    excluded_records: int
    unpaired_acquisitions: int


def _fraction(n: int, d: int) -> float:
    return n / d if d else np.nan


def diagnose_overlap(
    detections: pd.DataFrame,
    cell_m: int = 1000,
    tolerance_minutes: int = 60,
    aoi_column: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    min_train_days: int = 20,
    min_validation_days: int = 10,
    min_matches: int = 20,
    bootstrap_samples: int = 1000,
    seed: int = 42,
) -> CalibrationResult:
    """Compare equal-area cells within one-to-one, nearest UTC acquisitions.

    Greedy chronological MODIS anchors use the nearest still-unused VIIRS time
    within tolerance, including across midnight, but never across years (to
    preserve the evaluation split). Exact ties choose earlier VIIRS.
    This deterministic matching is not a model of actual swath coverage.
    Month/year/day belong to the MODIS anchor. AOIs are analyzed independently;
    without an AOI column the caller's selected region is one AOI.

    Per AOI/calendar month, reserve the latest paired year for validation.
    Fit the geometric mean of daily MODIS/VIIRS cell-period ratios on at least
    two earlier years. Bootstrap whole training years, preserving dependence
    within each year. This estimates a conditional count-scale adjustment only.
    """
    if not 375 <= cell_m <= 10000:
        raise ValueError("cell_m debe estar entre 375 y 10 000 m")
    if not 1 <= tolerance_minutes <= 180:
        raise ValueError("La tolerancia debe estar entre 1 y 180 minutos")
    if min(min_train_days, min_validation_days, min_matches) < 1 or bootstrap_samples < 100:
        raise ValueError("Soporte positivo y al menos 100 réplicas bootstrap requeridos")
    required = {"latitude", "longitude", "acquired_utc", "sensor"}
    if not required.issubset(detections.columns):
        raise ValueError(f"Faltan columnas: {sorted(required - set(detections.columns))}")
    data = detections.copy()
    data["acquired_utc"] = pd.to_datetime(data.acquired_utc, utc=True, errors="coerce")
    for name in ("latitude", "longitude"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    valid = (data.acquired_utc.dt.year.ge(2012) & data.sensor.isin(["MODIS", "VIIRS"])
             & data.latitude.between(-85, 85) & data.longitude.between(-180, 180))
    if bbox is not None:
        west, south, east, north = bbox
        if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
            raise ValueError("BBox inválido")
        valid &= data.longitude.between(west, east) & data.latitude.between(south, north)
    if aoi_column is not None:
        if aoi_column not in data:
            raise ValueError("Columna AOI inexistente")
        valid &= data[aoi_column].notna()
        data["aoi"] = data[aoi_column].astype(str)
    else:
        data["aoi"] = "AOI seleccionada"
    excluded = int((~valid).sum())
    data = data.loc[valid].copy()
    x, y = _FORWARD.transform(data.longitude.to_numpy(), data.latitude.to_numpy())
    data["gx"] = np.floor(np.asarray(x) / cell_m).astype("int64")
    data["gy"] = np.floor(np.asarray(y) / cell_m).astype("int64")
    rows, unpaired = [], 0
    tolerance = pd.Timedelta(int(tolerance_minutes) * 60, unit="s")
    for aoi, area in data.groupby("aoi", sort=True):
        acquisitions = {}
        for sensor in ("MODIS", "VIIRS"):
            acquisitions[sensor] = {
                time: set(zip(group.gx, group.gy))
                for time, group in area.loc[area.sensor == sensor].groupby("acquired_utc", sort=True)
            }
        modis, viirs = acquisitions["MODIS"], acquisitions["VIIRS"]
        # Sorted available timestamps allow local searches without an all-pairs matrix.
        available = sorted(viirs)
        paired = 0
        for mt, mcells in modis.items():
            pos = bisect.bisect_left(available, mt)
            candidates = [t for t in available[max(0, pos - 1):pos + 1] if t.year == mt.year]
            if not candidates:
                continue
            vt = min(candidates, key=lambda t: (abs(t - mt), t))
            if abs(vt - mt) > tolerance:
                continue
            available.remove(vt)
            vcells = viirs[vt]
            shared = len(mcells & vcells)
            rows.append(dict(aoi=aoi, modis_time=mt, viirs_time=vt,
                             date=mt.date(), year=mt.year, month=mt.month,
                             lag_minutes=abs((vt - mt).total_seconds()) / 60,
                             modis_cells=len(mcells), viirs_cells=len(vcells),
                             matched_cells=shared, union_cells=len(mcells | vcells)))
            paired += 1
        unpaired += len(modis) + len(viirs) - 2 * paired
    periods = pd.DataFrame(rows, columns=["aoi", "modis_time", "viirs_time", "date", "year", "month",
                                         "lag_minutes", "modis_cells", "viirs_cells", "matched_cells", "union_cells"])
    monthly_rows = []
    for (aoi, year, month), group in periods.groupby(["aoi", "year", "month"]):
        m, v, shared, union = [int(group[c].sum()) for c in
                              ("modis_cells", "viirs_cells", "matched_cells", "union_cells")]
        monthly_rows.append(dict(aoi=aoi, year=year, month=month,
                                 paired_periods=len(group), paired_days=group.date.nunique(),
                                 modis_cells=m, viirs_cells=v, matched_cells=shared,
                                 modis_only=m-shared, viirs_only=v-shared,
                                 jaccard=_fraction(shared, union),
                                 viirs_given_modis=_fraction(shared, m),
                                 modis_given_viirs=_fraction(shared, v),
                                 relative_count_difference=_fraction(v-m, m)))
    monthly = pd.DataFrame(monthly_rows, columns=["aoi", "year", "month", "paired_periods", "paired_days",
                                                 "modis_cells", "viirs_cells", "matched_cells", "modis_only", "viirs_only",
                                                 "jaccard", "viirs_given_modis", "modis_given_viirs", "relative_count_difference"])
    normalization = _normalize(periods, min_train_days, min_validation_days,
                               min_matches, bootstrap_samples, seed)
    return CalibrationResult(periods, monthly, normalization, excluded, unpaired)


def _normalize(periods, min_train_days, min_validation_days, min_matches, samples, seed):
    rng = np.random.default_rng(seed)
    rows = []
    for (aoi, month), group in periods.groupby(["aoi", "month"]):
        years = sorted(group.year.unique())
        validation_year = int(years[-1])
        train = group.loc[group.year < validation_year]
        validation = group.loc[group.year == validation_year]
        daily = train.groupby(["year", "date"])[["modis_cells", "viirs_cells"]].sum()
        td, vd = len(daily), validation.date.nunique()
        row = dict(aoi=aoi, month=month, train_years=", ".join(map(str, years[:-1])),
                   validation_year=validation_year, train_days=td, validation_days=vd,
                   train_matches=int(train.matched_cells.sum()),
                   validation_matches=int(validation.matched_cells.sum()),
                   annual_ratio_min=np.nan, annual_ratio_max=np.nan,
                   factor_viirs_to_modis=np.nan, factor_ci_low=np.nan, factor_ci_high=np.nan,
                   observed_modis=int(validation.modis_cells.sum()),
                   observed_viirs=int(validation.viirs_cells.sum()),
                   reconciled_viirs=np.nan, reconciled_ci_low=np.nan, reconciled_ci_high=np.nan,
                   raw_validation_mae=np.nan, adjusted_validation_mae=np.nan)
        reasons = []
        if len(years) < 3:
            reasons.append("se requieren 2 años de entrenamiento y 1 posterior de validación")
        if td < min_train_days or vd < min_validation_days:
            reasons.append(f"días emparejados insuficientes (mínimos {min_train_days}/{min_validation_days})")
        if train.matched_cells.sum() < min_matches or validation.matched_cells.sum() < min_matches:
            reasons.append(f"coincidencias insuficientes (mínimo {min_matches} en cada partición)")
        if reasons:
            row.update(status="insuficiente información", reason="; ".join(reasons))
        else:
            logs = np.log(daily.modis_cells / daily.viirs_cells)
            blocks = [logs.loc[y].to_numpy() for y in years[:-1]]
            annual = np.exp([b.mean() for b in blocks])
            factor = float(np.exp(logs.mean()))
            draws = np.empty(samples)
            for i in range(samples):
                selected = rng.integers(0, len(blocks), len(blocks))
                draws[i] = np.exp(np.concatenate([blocks[j] for j in selected]).mean())
            low, high = np.quantile(draws, [.025, .975])
            heldout = validation.groupby("date")[["modis_cells", "viirs_cells"]].sum()
            row.update(status="experimental; no validada científicamente", reason="soporte mínimo satisfecho; cobertura no verificada",
                       annual_ratio_min=float(min(annual)), annual_ratio_max=float(max(annual)),
                       factor_viirs_to_modis=factor, factor_ci_low=float(low), factor_ci_high=float(high),
                       reconciled_viirs=row["observed_viirs"] * factor,
                       reconciled_ci_low=row["observed_viirs"] * low,
                       reconciled_ci_high=row["observed_viirs"] * high,
                       raw_validation_mae=float(abs(heldout.viirs_cells-heldout.modis_cells).mean()),
                       adjusted_validation_mae=float(abs(heldout.viirs_cells*factor-heldout.modis_cells).mean()))
        rows.append(row)
    return pd.DataFrame(rows, columns=["aoi", "month", "train_years", "validation_year", "train_days", "validation_days",
                                       "train_matches", "validation_matches", "annual_ratio_min", "annual_ratio_max",
                                       "factor_viirs_to_modis", "factor_ci_low", "factor_ci_high", "observed_modis", "observed_viirs",
                                       "reconciled_viirs", "reconciled_ci_low", "reconciled_ci_high", "raw_validation_mae",
                                       "adjusted_validation_mae", "status", "reason"])
