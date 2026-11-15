"""All fixtures are artificial; these tests are not satellite validation."""
import numpy as np
import pandas as pd
import pytest
from pyproj import Transformer

from firesync.calibration import diagnose_overlap


def detections(rows):
    return pd.DataFrame(rows, columns=["acquired_utc", "sensor", "latitude", "longitude"])


def pair(mt="2024-01-01T12:00Z", vt="2024-01-01T12:30Z", lon=0.001):
    return [(mt, "MODIS", 0.001, 0.001), (vt, "VIIRS", 0.001, lon)]


def test_identical_cells_and_duplicate_invariance():
    result = diagnose_overlap(detections(pair() * 2))
    row = result.monthly.iloc[0]
    assert row.modis_cells == row.viirs_cells == row.matched_cells == 1
    assert row.jaccard == row.viirs_given_modis == row.modis_given_viirs == 1
    assert result.normalization.iloc[0].status == "insuficiente información"


def test_noncoincident_detections_are_not_truth_labels():
    row = diagnose_overlap(detections(pair(lon=1))).monthly.iloc[0]
    assert row.matched_cells == row.jaccard == 0
    assert row.modis_only == row.viirs_only == 1


@pytest.mark.parametrize("rows", [pair("2011-01-01T12:00Z", "2011-01-01T12:00Z"),
                                  pair("2011-01-01T12:00Z", "2012-01-01T12:00Z"),
                                  pair(vt="2024-01-01T13:01Z"), []])
def test_no_temporal_overlap(rows):
    result = diagnose_overlap(detections(rows))
    assert result.periods.empty and result.normalization.empty


def test_midnight_and_month_boundary_and_tolerance_inclusive():
    result = diagnose_overlap(detections(pair("2024-01-31T23:30Z", "2024-02-01T00:30Z")))
    row = result.periods.iloc[0]
    assert row.year == 2024 and row.month == 1 and row.lag_minutes == 60


def test_pairs_cannot_cross_years_and_leak_into_validation():
    result = diagnose_overlap(detections(pair("2023-12-31T23:30Z", "2024-01-01T00:30Z")))
    assert result.periods.empty and result.unpaired_acquisitions == 2


def test_one_to_one_acquisitions_no_reuse():
    rows = pair() + [("2024-01-01T12:10Z", "MODIS", 0.001, 0.001)]
    result = diagnose_overlap(detections(rows))
    assert len(result.periods) == 1 and result.unpaired_acquisitions == 1


def test_cell_boundaries_are_floor_based_including_negative_coordinates():
    inverse = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
    for boundary in (-1000, 0, 1000):
        left = inverse.transform(boundary - .01, 100)
        right = inverse.transform(boundary + .01, 100)
        rows = [("2024-01-01T12:00Z", "MODIS", left[1], left[0]),
                ("2024-01-01T12:00Z", "VIIRS", right[1], right[0])]
        result = diagnose_overlap(detections(rows))
        assert result.monthly.iloc[0].matched_cells == 0


def supported_rows(validation_extra=0):
    rows = []
    for year in (2022, 2023, 2024):
        for day in range(1, 11):
            time = f"{year}-01-{day:02d}T12:00Z"
            rows.extend(pair(time, time))
            rows.append((time, "VIIRS", .001, .02))
            if year == 2024:
                for i in range(validation_extra):
                    rows.append((time, "VIIRS", .001, .04 + i*.02))
    return rows


def test_supported_normalization_bootstrap_and_heldout_metrics():
    result = diagnose_overlap(detections(supported_rows()), min_matches=10)
    row = result.normalization.iloc[0]
    assert row.train_years == "2022, 2023" and row.validation_year == 2024
    assert row.train_days == 20 and row.validation_days == 10
    assert row.factor_viirs_to_modis == pytest.approx(.5)
    assert row.factor_ci_low == row.factor_ci_high == pytest.approx(.5)
    assert row.observed_modis == row.reconciled_viirs == 10
    assert row.observed_viirs == 20
    assert row.raw_validation_mae == 1 and row.adjusted_validation_mae == 0


def test_validation_detections_do_not_change_fit_or_bootstrap():
    first = diagnose_overlap(detections(supported_rows()), min_matches=10).normalization.iloc[0]
    changed = diagnose_overlap(detections(supported_rows(3)), min_matches=10).normalization.iloc[0]
    for col in ("factor_viirs_to_modis", "factor_ci_low", "factor_ci_high"):
        assert first[col] == changed[col]
    assert changed.adjusted_validation_mae > first.adjusted_validation_mae


def test_monthly_factors_not_global_ratios_and_annual_variability():
    rows = supported_rows()
    rows += [("2023-01-01T12:00Z", "VIIRS", .001, .06)]
    rows += [(t.replace("-01-", "-02-"), s, lat, lon) for t, s, lat, lon in supported_rows() if lon == .001]
    result = diagnose_overlap(detections(rows), min_matches=10).normalization
    assert result.loc[result.month == 2, "factor_viirs_to_modis"].iloc[0] == 1
    jan = result.loc[result.month == 1].iloc[0]
    assert jan.annual_ratio_min < jan.annual_ratio_max
    assert jan.factor_ci_low < jan.factor_ci_high


def test_aoi_separation_and_bbox_do_not_create_cross_area_matches():
    data = detections(pair())
    data["zone"] = ["west", "east"]
    assert diagnose_overlap(data, aoi_column="zone").periods.empty
    result = diagnose_overlap(detections(pair(lon=1)), bbox=(-.1, -.1, .1, .1))
    assert result.periods.empty and result.excluded_records == 1


def test_insufficient_matches_never_yield_factor():
    result = diagnose_overlap(detections(supported_rows())).normalization.iloc[0]
    assert result.status == "insuficiente información"
    assert np.isnan(result.factor_viirs_to_modis) and np.isnan(result.reconciled_ci_low)


def test_input_unchanged_and_invalid_configuration():
    data = detections(pair())
    original = data.copy(deep=True)
    diagnose_overlap(data)
    pd.testing.assert_frame_equal(data, original)
    for kwargs in ({"cell_m": 0}, {"tolerance_minutes": 0}, {"bootstrap_samples": 1}, {"bbox": (1, 1, 0, 0)}):
        with pytest.raises(ValueError):
            diagnose_overlap(data, **kwargs)


def test_invalid_dates_coordinates_sensors_are_excluded():
    data = detections(pair() + [("bad", "MODIS", 0, 0),
                               ("2024-01-01T12:00Z", "OTHER", 0, 0),
                               ("2024-01-01T12:00Z", "VIIRS", 90, 0)])
    result = diagnose_overlap(data)
    assert result.excluded_records == 3 and len(result.periods) == 1
