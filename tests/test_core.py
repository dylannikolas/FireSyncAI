from datetime import date
import pandas as pd
import pytest
from firesync.core import normalize_firms, aggregate_cells, confidence_filter, monthly_activity, historical_anomalies


def df_sample():
    return pd.DataFrame([
        dict(latitude=-9.3000, longitude=-74.0000, acq_date="2025-10-01", acq_time=210, satellite="Terra", instrument="MODIS", confidence=60, frp=5),
        dict(latitude=-9.3001, longitude=-74.0001, acq_date="2025-10-01", acq_time=215, satellite="N20", instrument="VIIRS", confidence="n", frp=7),
        dict(latitude=-9.3001, longitude=-74.0001, acq_date="2025-10-02", acq_time=215, satellite="N20", instrument="VIIRS", confidence="l", frp=7),
    ])


def test_parse_hhmm_and_sensors():
    result = normalize_firms(df_sample())
    assert len(result) == 3
    assert str(result.iloc[0].acquired_utc) == "2025-10-01 02:10:00+00:00"
    assert set(result.sensor) == {"MODIS", "VIIRS"}


def test_cell_day_combines_detections_without_mixing_days():
    cells = aggregate_cells(normalize_firms(df_sample()), 1000)
    assert len(cells) == 2
    same = cells.loc[cells.date == date(2025, 10, 1)].iloc[0]
    assert same.raw_count == 2 and same.modis_seen and same.viirs_seen


def test_quality_filter_has_separate_rules():
    raw = normalize_firms(df_sample())
    kept = confidence_filter(raw, modis_min=50, exclude_viirs_low=True)
    assert len(kept) == 2
    assert set(kept.confidence) == {"60", "n"}


def test_anomaly_needs_prior_years():
    samples = pd.DataFrame([dict(year=y, month=8, active_cell_days=n) for y,n in [(2022,10),(2023,12),(2024,44)]])
    result = historical_anomalies(samples)
    assert pd.isna(result.iloc[1].ratio)
    assert result.iloc[2].ratio == 4


def test_unknown_sensor_rejected():
    df = df_sample().drop(columns=["satellite", "instrument"])
    with pytest.raises(ValueError):
        normalize_firms(df)
