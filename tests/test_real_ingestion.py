"""Regression fixtures are synthetic; optional local-data tests are identified."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from firesync.history import import_csv, import_file, discover_local_files, file_sha256
from firesync.calendar import daily_sensor_activity
from firesync.validated_data import load_observational_bundle, REAL_AUGUST_BUNDLE


def payload(sensor="MODIS"):
    return pd.DataFrame([dict(latitude=-9.3, longitude=-74., acq_date="2024-08-01", acq_time="0210",
                              instrument="SNPP" if sensor == "VIIRS" else "MODIS",
                              satellite="SNPP" if sensor == "VIIRS" else "Aqua",
                              version="2" if sensor == "VIIRS" else "61.03",
                              confidence="n" if sensor == "VIIRS" else "80")]).to_csv(index=False).encode()


@pytest.mark.parametrize("sensor,product", [("MODIS", "MODIS_C61"), ("VIIRS", "VIIRS_SNPP_C2")])
def test_archive_label_regressions_preserve_original_values(sensor, product):
    result = import_csv(payload(sensor), "ARTIFICIAL.csv", product, data_kind="synthetic")
    assert len(result.observations) == 1
    row = result.observations.iloc[0]
    assert row.sensor == sensor
    assert row.instrument_original == ("SNPP" if sensor == "VIIRS" else "MODIS")
    assert row.version == ("2" if sensor == "VIIRS" else "61.03")


def test_chunked_import_equivalence_dedup_and_source_row_across_boundaries(tmp_path):
    import io
    row = pd.read_csv(io.BytesIO(payload()), dtype=str).to_dict("records")[0]
    rows = [dict(row, longitude="0"), row, dict(row, acq_date="2024-08-02"), row]
    content = pd.DataFrame(rows).to_csv(index=False).encode()
    path = tmp_path / "ARTIFICIAL.csv"
    path.write_bytes(content)
    expected = import_csv(content, path.name, "MODIS_C61", data_kind="synthetic")
    result = import_file(path, "MODIS_C61", chunksize=2, data_kind="synthetic")
    pd.testing.assert_frame_equal(expected.observations, result.observations)
    assert result.manifest["duplicate_rows"] == 1
    assert result.manifest["input_rows"] == 4 and result.manifest["excluded_rows"] == 1
    assert result.observations.source_row.tolist() == [3, 4]
    assert result.manifest["input_audit"]["aoi_rows_before_quality"] == 3
    assert result.manifest["sha256"] == hashlib.sha256(content).hexdigest()
    assert path.read_bytes() == content


def test_file_discovery_supports_root_and_previous_subfolders_without_cross_sensor(tmp_path):
    for name in ("fire_archive_M-C61_123.csv", "fire_archive_SV-C2_456.csv", "unrelated.csv"):
        (tmp_path / name).touch()
    (tmp_path / "modis").mkdir()
    (tmp_path / "modis/legacy.csv").touch()
    assert {p.name for p in discover_local_files("MODIS_C61", tmp_path)} == {"fire_archive_M-C61_123.csv", "legacy.csv"}
    assert [p.name for p in discover_local_files("VIIRS_SNPP_C2", tmp_path)] == ["fire_archive_SV-C2_456.csv"]


def test_daily_counts_keep_records_distinct_from_cells_and_unknown_sensor():
    modis = import_csv(payload(), "ARTIFICIAL_M.csv", "MODIS_C61", data_kind="synthetic").observations
    viirs = import_csv(payload("VIIRS"), "ARTIFICIAL_V.csv", "VIIRS_SNPP_C2", data_kind="synthetic").observations
    viirs["date"] = viirs["date"] + pd.Timedelta(1, unit="d")
    viirs["acquired_utc"] += pd.Timedelta(1, unit="d")
    data = pd.concat([modis, modis, viirs], ignore_index=True)
    result = daily_sensor_activity(data)
    assert result.iloc[0].modis_detections == 2 and result.iloc[0].modis_cell_days == 1
    assert pd.isna(result.iloc[0].viirs_detections)
    assert pd.isna(result.iloc[1].modis_detections)
    assert result.iloc[1].viirs_cell_days == 1 and len(result) == 2
    assert daily_sensor_activity(data.iloc[:0]).empty


def test_processed_observational_bundle_rejects_synthetic_or_tampered_output(tmp_path):
    folder = tmp_path / "bundle"
    folder.mkdir()
    manifest_path = folder / "manifest.json"
    manifest_path.write_text(json.dumps(dict(observation_kind="synthetic")))
    with pytest.raises(ValueError, match="sintéticos"):
        load_observational_bundle(folder)
    output = folder / "observations.csv"
    output.write_text("original")
    manifest_path.write_text(json.dumps(dict(observation_kind="user_supplied_unverified", output_sha256={"observations.csv": file_sha256(output)})))
    output.write_text("modified")
    with pytest.raises(ValueError, match="Salida modificada"):
        load_observational_bundle(folder)


@pytest.mark.skipif(not (REAL_AUGUST_BUNDLE / "manifest.json").exists(), reason="Requiere originales locales y validación real de agosto 2024")
def test_local_real_observations_reproduce_counts_calendar_and_no_calibration():
    """This test actually reads the user's real local data, never a mock."""
    from firesync.history import combine_imports
    from firesync.calendar import sensor_calendar
    from firesync.calibration import diagnose_overlap
    imports = load_observational_bundle(REAL_AUGUST_BUNDLE)
    data, manifest = combine_imports(imports)
    assert data.sensor.value_counts().to_dict() == {"VIIRS": 13905, "MODIS": 2931}
    assert len(data) == 16836 and not data.data_kind.eq("synthetic").any()
    assert data.acquired_utc.dt.strftime("%Y-%m").unique().tolist() == ["2024-08"]
    calendar = sensor_calendar(data).iloc[0]
    assert calendar.modis_cell_days == 2804 and calendar.viirs_cell_days == 10581
    assert calendar.observed_union_cell_days == 12735
    diagnosis = diagnose_overlap(data)
    row = diagnosis.monthly.iloc[0]
    assert row.paired_periods == 41 and row.paired_days == 21 and row.matched_cells == 51
    assert diagnosis.normalization.iloc[0].status == "insuficiente información"
    assert pd.isna(diagnosis.normalization.iloc[0].factor_viirs_to_modis)


@pytest.mark.skipif(not (REAL_AUGUST_BUNDLE / "manifest.json").exists(), reason="Requiere originales y resultados reales locales")
def test_real_data_dashboard_map_calendar_and_daily_series():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file("app.py", default_timeout=120)
    app.query_params["source"] = "real"
    app.run()
    assert not app.exception
    assert app.radio[0].value == "Observaciones FIRMS · agosto 2024 (AOI)"
    assert app.metric[0].value == "16,836" and app.metric[1].value == "12,735"
    assert app.metric[2].value == "2,931" and app.metric[3].value == "13,905"
    assert len(app.get("deck_gl_json_chart")) == 1
    assert len(app.get("plotly_chart")) == 1
    frames = [frame.value for frame in app.dataframe]
    daily = next(frame for frame in frames if "modis_detections" in frame)
    assert daily.modis_detections.sum() == 2931 and daily.viirs_detections.sum() == 13905
    assert len(daily) == 31
    assert not any("DATOS SINTÉTICOS" in warning.value for warning in app.warning)
    next(s for s in app.selectbox if s.label == "Serie del calendario").select("Reconciliada experimental (celdas-periodo)").run()
    assert not app.exception
    assert any("Sin información suficiente" in i.value for i in app.info)
