"""Minimal NASA FIRMS recent Area API client. Keep MAP_KEY private."""
from __future__ import annotations
import io
import pandas as pd
import requests
from datetime import date, timedelta
import hashlib

SOURCES = ("MODIS_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT")


def fetch_recent_area(map_key: str, source: str, bbox: tuple[float, float, float, float], days: int = 3) -> pd.DataFrame:
    if not map_key or not map_key.strip():
        raise ValueError("Falta MAP_KEY de FIRMS")
    if source not in SOURCES:
        raise ValueError("Fuente NASA no admitida")
    if not (1 <= days <= 5):
        raise ValueError("NASA FIRMS admite un intervalo de 1 a 5 días por solicitud")
    west, south, east, north = [float(v) for v in bbox]
    if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
        raise ValueError("BBox inválido: oeste,sur,este,norte")
    coordinates = ",".join(f"{v:g}" for v in [west, south, east, north])
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key.strip()}/{source}/{coordinates}/{days}"
    try:
        response = requests.get(url, timeout=35)
        response.raise_for_status()
    except requests.RequestException as exc:
        # Do not surface the underlying request URL: it includes the secret MAP_KEY.
        raise RuntimeError("No se pudo consultar la API FIRMS; comprueba conexión, clave o cuota.") from None
    if not response.text.strip():
        return pd.DataFrame()
    try:
        result = pd.read_csv(io.StringIO(response.text))
    except Exception:
        raise RuntimeError("NASA FIRMS no respondió con un CSV válido.") from None
    if not {"latitude", "longitude", "acq_date", "acq_time"}.issubset({str(c).lower() for c in result.columns}):
        raise RuntimeError("Respuesta FIRMS sin el esquema esperado; comprueba MAP_KEY/cuota.")
    return result

# Public, recent global CSV files published by NASA FIRMS.
PUBLIC_24H = {
    "MODIS": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv",
    "VIIRS_NOAA20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
    "VIIRS_SNPP": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
}


def fetch_public_24h(source: str, bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """Read a public 24-hour global CSV and filter a user-selected bounding box.

    This alternative does not require MAP_KEY but is not guaranteed to be available
    without authentication in every deployment/network.
    """
    if source not in PUBLIC_24H:
        raise ValueError("Fuente pública no admitida")
    west, south, east, north = [float(v) for v in bbox]
    if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
        raise ValueError("BBox inválido: oeste,sur,este,norte")
    try:
        resp = requests.get(PUBLIC_24H[source], timeout=60)
        resp.raise_for_status()
        table = pd.read_csv(io.BytesIO(resp.content))
    except (requests.RequestException, pd.errors.ParserError, UnicodeDecodeError) as err:
        raise RuntimeError("No se pudo descargar el CSV público NASA. Prueba con MAP_KEY o carga archivos locales.") from None
    table.columns = table.columns.astype(str).str.lower().str.strip()
    if not {"latitude", "longitude", "acq_date", "acq_time"}.issubset(set(table.columns)):
        raise RuntimeError("El archivo NASA descargado no contiene las columnas esperadas")
    lat = pd.to_numeric(table["latitude"], errors="coerce")
    lon = pd.to_numeric(table["longitude"], errors="coerce")
    return table.loc[lat.between(south, north) & lon.between(west, east)].reset_index(drop=True)


HISTORICAL_SOURCES = {"MODIS_C61": "MODIS_SP", "VIIRS_SNPP_C2": "VIIRS_SNPP_SP"}


def fetch_historical_area(map_key: str, product: str, bbox, start: str, end: str) -> pd.DataFrame:
    """Fetch a small SP subset in <=5-day requests; fail atomically on errors.

    Availability is controlled by FIRMS. Empty CSV is not evidence of valid
    coverage or zero fires. The secret URL never appears in raised exceptions.
    """
    from firesync.history import validate_bbox, OVERLAP_START
    if not map_key or not map_key.strip():
        raise ValueError("Falta MAP_KEY de FIRMS")
    if product not in HISTORICAL_SOURCES:
        raise ValueError("Producto histórico no admitido")
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError):
        raise ValueError("Fechas ISO YYYY-MM-DD requeridas") from None
    if first < date.fromisoformat(OVERLAP_START) or last < first or last > date.today():
        raise ValueError("Periodo histórico inválido")
    if (last-first).days >= 31:
        raise ValueError("Consulta un subconjunto de hasta 31 días; usa CSV para series largas")
    coordinates = ",".join(f"{v:g}" for v in validate_bbox(bbox))
    frames, audit = [], []
    cursor = first
    while cursor <= last:
        days = min(5, (last-cursor).days+1)
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key.strip()}/"
               f"{HISTORICAL_SOURCES[product]}/{coordinates}/{days}/{cursor.isoformat()}")
        try:
            response = requests.get(url, timeout=35)
            response.raise_for_status()
            table = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
            table.columns = table.columns.str.strip().str.lower()
            if not {"latitude", "longitude", "acq_date", "acq_time", "satellite", "version", "confidence"}.issubset(table):
                raise ValueError("Esquema inesperado")
        except (requests.RequestException, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
            raise RuntimeError("No se pudo obtener el CSV histórico FIRMS; comprueba red, disponibilidad SP, clave o cuota. No se aceptaron resultados parciales.") from None
        frames.append(table)
        audit.append(dict(source=HISTORICAL_SOURCES[product], start=cursor.isoformat(), days=days,
                          response_text_sha256=hashlib.sha256(response.text.encode("utf-8")).hexdigest(), rows=len(table)))
        cursor += timedelta(days=days)
    result = pd.concat(frames, ignore_index=True)
    result.attrs["api_requests"] = audit
    return result
