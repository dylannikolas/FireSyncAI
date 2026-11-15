"""Mocked API responses are artificial and never evidence of real NASA data."""
from types import SimpleNamespace
import pandas as pd
import pytest
import requests

from firesync.nasa import fetch_historical_area

BBOX = (-76.5, -12.5, -72., -7.)
HEADER = "latitude,longitude,acq_date,acq_time,satellite,version,confidence\n"


def response(text):
    return SimpleNamespace(text=text, raise_for_status=lambda: None)


def test_api_date_windows_are_inclusive_nonoverlapping_and_at_most_five_days(monkeypatch):
    urls = []
    def get(url, **kwargs):
        urls.append(url)
        return response(HEADER)
    monkeypatch.setattr(requests, "get", get)
    result = fetch_historical_area("TEST_NOT_A_REAL_KEY", "VIIRS_SNPP_C2", BBOX, "2023-08-01", "2023-08-12")
    assert result.empty and len(urls) == 3
    assert urls[0].endswith("/5/2023-08-01") and urls[1].endswith("/5/2023-08-06")
    assert urls[2].endswith("/2/2023-08-11") and "VIIRS_SNPP_SP" in urls[0]


def test_api_never_returns_partial_data_or_leaks_key_in_error(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return response(HEADER + "-9,-74,2023-08-01,1200,T,6.1,80\n")
        raise requests.ConnectionError("MOCK_PRIVATE_KEY inside error")
    monkeypatch.setattr(requests, "get", get)
    with pytest.raises(RuntimeError) as error:
        fetch_historical_area("MOCK_PRIVATE_KEY", "MODIS_C61", BBOX, "2023-08-01", "2023-08-06")
    assert "MOCK_PRIVATE_KEY" not in str(error.value)
    assert "parciales" in str(error.value) and len(calls) == 2


@pytest.mark.parametrize("text", ["", "<html>server error</html>", "latitude,longitude\n1,2"])
def test_api_bad_csv_does_not_masquerade_as_no_detections(monkeypatch, text):
    monkeypatch.setattr(requests, "get", lambda *a, **k: response(text))
    with pytest.raises(RuntimeError):
        fetch_historical_area("TEST", "MODIS_C61", BBOX, "2023-08-01", "2023-08-01")


@pytest.mark.parametrize("key,product,start,end", [
    ("", "MODIS_C61", "2023-08-01", "2023-08-01"),
    ("TEST", "VIIRS_NOAA20", "2023-08-01", "2023-08-01"),
    ("TEST", "MODIS_C61", "2011-01-01", "2011-01-02"),
    ("TEST", "MODIS_C61", "2023-08-02", "2023-08-01"),
    ("TEST", "MODIS_C61", "2023-08-01", "2023-09-01"),
])
def test_api_invalid_requests_make_no_network_calls(monkeypatch, key, product, start, end):
    def forbidden(*args, **kwargs):
        pytest.fail("La solicitud inválida no debe consultar la red")
    monkeypatch.setattr(requests, "get", forbidden)
    with pytest.raises(ValueError):
        fetch_historical_area(key, product, BBOX, start, end)
