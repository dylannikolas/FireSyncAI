"""Artificial FIRMS-shaped fixtures only; no authentic satellite observations."""
import hashlib
import io
import json

import pandas as pd
import pytest

from firesync.history import import_csv, combine_imports, main, REGIONS
from firesync.calendar import sensor_calendar, experimental_calendar


def csv_bytes(rows=None, **changes):
    row = dict(latitude="-9.3", longitude="-74.0", acq_date="2023-08-01", acq_time="0210",
               satellite="Terra", instrument="MODIS", confidence="80", version="6.1", frp="5", scan="1.2", track="1.1")
    row.update(changes)
    return pd.DataFrame(rows if rows is not None else [row]).to_csv(index=False).encode("utf-8")


def import_fixture(payload=None, product="MODIS_C61", **kwargs):
    return import_csv(payload or csv_bytes(), "ARTIFICIAL.csv", product, data_kind="synthetic", **kwargs)


def test_metadata_original_dates_resolution_hash_and_no_mutation():
    payload = csv_bytes()
    result = import_fixture(payload)
    row = result.observations.iloc[0]
    assert row.acq_date_original == "2023-08-01" and row.acq_time_original == "0210"
    assert str(row.acquired_utc) == "2023-08-01 02:10:00+00:00"
    assert row.source_row == 2 and row.nominal_resolution_m == 1000
    assert row.satellite == "TERRA" and row.collection == "6.1"
    assert row.scan == "1.2" and row.track == "1.1" and row.processing == "SP"
    assert row.source_sha256 == hashlib.sha256(payload).hexdigest()
    assert row.data_kind == "synthetic"
    assert result.manifest["accepted_rows"] == 1 and result.manifest["excluded_rows"] == 0


@pytest.mark.parametrize("satellite", ["N", "SNPP", "Suomi-NPP"])
def test_snpp_collection_2_preserves_nominal_375m(satellite):
    result = import_fixture(csv_bytes(satellite=satellite, instrument="VIIRS", confidence="n", version="2"), "VIIRS_SNPP_C2")
    assert result.observations.iloc[0].nominal_resolution_m == 375
    assert result.observations.iloc[0].sensor == "VIIRS"


@pytest.mark.parametrize("changes,reason", [
    ({"acq_time": "2400"}, "invalid_time"),
    ({"acq_time": "1260"}, "invalid_time"),
    ({"acq_date": "2023-02-29"}, "invalid_date"),
    ({"acq_date": "2023-08-01T00:00Z"}, "invalid_date"),
    ({"acq_date": "2012-01-19"}, "outside_period"),
    ({"latitude": "91"}, "invalid_coordinates"),
    ({"longitude": "0"}, "outside_aoi"),
    ({"version": "6.0"}, "wrong_collection"),
    ({"version": "6.1NRT"}, "nrt_not_allowed"),
    ({"satellite": "NOAA-20"}, "wrong_satellite"),
    ({"instrument": "VIIRS"}, "wrong_instrument"),
    ({"confidence": "n"}, "invalid_sensor_confidence"),
])
def test_invalid_rows_are_reported_without_inventing_zeros(changes, reason):
    result = import_fixture(csv_bytes(**changes))
    assert result.observations.empty
    assert result.manifest["excluded_rows"] == 1
    assert result.manifest["rejection_reasons"][reason] == 1
    assert result.manifest["observed_start"] is None


def test_viirs_noaa20_and_collection1_cannot_be_mislabeled_as_snpp_c2():
    result = import_fixture(csv_bytes(satellite="N20", instrument="VIIRS", version="1", confidence="n"), "VIIRS_SNPP_C2")
    assert result.observations.empty
    assert result.manifest["rejection_reasons"]["wrong_collection"] == 1
    assert result.manifest["rejection_reasons"]["wrong_satellite"] == 1


def test_leap_date_boundary_date_and_zero_padded_hhmm():
    result = import_fixture(csv_bytes(acq_date="2024-02-29", acq_time="5"), start="2024-02-29", end="2024-02-29")
    assert str(result.observations.iloc[0].acquired_utc) == "2024-02-29 00:05:00+00:00"
    first = import_fixture(csv_bytes(acq_date="2012-01-20"))
    assert len(first.observations) == 1


def test_duplicates_within_and_across_files_and_original_row_alignment():
    rows = pd.read_csv(io.BytesIO(csv_bytes()), dtype=str).to_dict("records")
    result = import_fixture(csv_bytes(rows=rows*2))
    assert len(result.observations) == 1 and result.manifest["duplicate_rows"] == 1
    combined, report = combine_imports([result, result])
    assert len(combined) == 1 and report["cross_file_duplicates"] == 1
    assert combined.iloc[0].source_row == 2


def test_nrt_is_explicit_and_distinct_from_sp_at_same_time_and_location():
    row = pd.read_csv(io.BytesIO(csv_bytes()), dtype=str).to_dict("records")[0]
    nrt = dict(row, version="6.1NRT")
    result = import_fixture(csv_bytes(rows=[row, nrt]), allow_nrt=True)
    assert len(result.observations) == 2
    assert set(result.observations.processing) == {"SP", "NRT"}


def test_header_only_is_valid_but_empty_bytes_html_and_wrong_schema_are_not():
    header = csv_bytes().decode().splitlines()[0].encode()
    result = import_fixture(header)
    assert result.observations.empty and result.manifest["input_rows"] == 0
    for payload in (b"", b"<html>not csv</html>", b"latitude,longitude\n1,2"):
        with pytest.raises(ValueError):
            import_csv(payload, "ARTIFICIAL.csv", "MODIS_C61")


def test_calendar_per_sensor_deduplicates_cell_days_and_keeps_unknowns():
    modis = import_fixture().observations
    viirs = import_fixture(csv_bytes(satellite="N", instrument="VIIRS", confidence="n", version="2", acq_date="2023-09-01"), "VIIRS_SNPP_C2").observations
    data = pd.concat([modis, modis, viirs])
    result = sensor_calendar(data)
    assert list(result.month) == [8, 9]
    assert result.iloc[0].modis_cell_days == 1 and pd.isna(result.iloc[0].viirs_cell_days)
    assert pd.isna(result.iloc[1].modis_cell_days) and result.iloc[1].viirs_cell_days == 1
    assert list(result.observed_union_cell_days) == [1, 1]
    assert sensor_calendar(data.iloc[:0]).empty
    assert experimental_calendar(pd.DataFrame()).empty


def test_experimental_calendar_only_exposes_supported_heldout_estimates():
    data = pd.DataFrame([dict(validation_year=2024, month=8, reconciled_viirs=12., observed_modis=10, observed_viirs=20,
                              reconciled_ci_low=8., reconciled_ci_high=15.),
                         dict(validation_year=2024, month=9, reconciled_viirs=float("nan"))])
    result = experimental_calendar(data)
    assert len(result) == 1 and result.iloc[0].year == 2024 and result.iloc[0].reconciled_ci_low == 8


def test_manual_provenance_never_claims_authenticated_nasa():
    result = import_csv(csv_bytes(), "local.csv", "MODIS_C61")
    assert result.manifest["data_kind"] == "user_supplied_unverified"
    assert result.observations.iloc[0].data_kind == "user_supplied_unverified"


def test_cli_produces_readable_empty_reports_and_refuses_overwrite(tmp_path):
    path = tmp_path / "ARTIFICIAL.csv"
    path.write_bytes(csv_bytes(longitude="0"))
    out = tmp_path / "result"
    argv = ["--modis", str(path), "--synthetic", "--output", str(out)]
    main(argv)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["accepted_rows"] == 0 and manifest["observation_kind"] == "synthetic"
    assert manifest["bootstrap_seed"] == 42 and "pandas" in manifest["dependencies"]
    for name in ("observations.csv", "calendar.csv", "overlap_monthly.csv", "overlap_pairs.csv", "evaluation.csv", "calendar_experimental.csv"):
        assert pd.read_csv(out / name).empty
    with pytest.raises(SystemExit):
        main(argv)


def test_invalid_region_and_dates_rejected():
    for kwargs in ({"bbox": (0, 0, -1, -1)}, {"start": "2011-01-01"}, {"start": "2024-01-01", "end": "2023-01-01"}):
        with pytest.raises(ValueError):
            import_fixture(**kwargs)
