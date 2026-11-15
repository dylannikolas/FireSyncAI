"""Reproducible, strict ingestion of declared FIRMS historical CSV products.

Metadata consistency is checked; a local file's authenticity cannot be proved
from its content. Raw files are never rewritten. Test fixtures are synthetic.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import platform
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from firesync.core import normalize_firms, confidence_filter

ARCHIVE_URL = "https://firms.modaps.eosdis.nasa.gov/download/"
OVERLAP_START = "2012-01-20"
# Approximate study boxes, NOT administrative or biome boundaries.
REGIONS = {
    "Amazonía peruana (AOI aproximada)": (-76.5, -12.5, -72.0, -7.0),
    "Ucayali (sub-AOI aproximada)": (-75.8, -10.8, -73.0, -7.2),
    "Madre de Dios (sub-AOI aproximada)": (-72.5, -13.5, -68.5, -10.0),
}
PRODUCTS = {
    "MODIS_C61": dict(sensor="MODIS", collection="6.1", nominal_resolution_m=1000,
                      satellites={"T", "A", "TERRA", "AQUA"}, standard={"6.1", "6.10", "61", "61.03"}),
    "VIIRS_SNPP_C2": dict(sensor="VIIRS", collection="2", nominal_resolution_m=375,
                          satellites={"N", "SNPP", "S-NPP", "SUOMI-NPP"}, standard={"2", "2.0", "2.00"}),
}
EMPTY_COLUMNS = ["latitude", "longitude", "acquired_utc", "date", "sensor", "satellite",
                 "confidence", "frp", "version", "acq_date_original", "acq_time_original",
                 "product", "collection", "nominal_resolution_m", "processing", "data_kind",
                 "source_file", "source_sha256", "source_row"]


@dataclass
class HistoricalImport:
    observations: pd.DataFrame
    manifest: dict


def validate_bbox(bbox):
    west, south, east, north = map(float, bbox)
    if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
        raise ValueError("BBox inválido: oeste,sur,este,norte")
    return west, south, east, north


def import_csv(
    payload: bytes,
    filename: str,
    product: str,
    bbox=REGIONS["Amazonía peruana (AOI aproximada)"],
    start: str = OVERLAP_START,
    end: str | None = None,
    allow_nrt: bool = False,
    data_kind: str = "user_supplied_unverified",
) -> HistoricalImport:
    """Validate row metadata, preserve original fields and report every rejection.

    product is an explicit user/source declaration, never inferred from an
    arbitrary filename. Row rejection reasons may overlap; excluded_rows is
    unique, and within-file duplicates are counted separately.
    """
    if product not in PRODUCTS:
        raise ValueError("Producto histórico no admitido")
    if data_kind not in {"user_supplied_unverified", "nasa_api", "synthetic"}:
        raise ValueError("Procedencia no admitida")
    west, south, east, north = validate_bbox(bbox)
    begin = pd.Timestamp(start, tz="UTC")
    finish = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC").normalize()
    if begin < pd.Timestamp(OVERLAP_START, tz="UTC") or finish < begin:
        raise ValueError("Periodo inválido; historial de coincidencia desde 2012-01-20")
    try:
        raw = pd.read_csv(io.BytesIO(payload), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise ValueError("El archivo no es un CSV FIRMS válido con cabecera") from None
    raw.columns = raw.columns.str.strip().str.lower()
    if raw.columns.duplicated().any():
        raise ValueError("Columnas duplicadas en CSV")
    required = {"latitude", "longitude", "acq_date", "acq_time", "satellite", "version", "confidence"}
    if not required.issubset(raw):
        raise ValueError(f"Columnas históricas faltantes: {', '.join(sorted(required-set(raw)))}")
    spec = PRODUCTS[product]
    dates = pd.to_datetime(raw.acq_date, format="%Y-%m-%d", utc=True, errors="coerce")
    date_ok = raw.acq_date.str.fullmatch(r"\d{4}-\d{2}-\d{2}") & dates.notna()
    times = raw.acq_time.str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(4)
    hh, mm = pd.to_numeric(times.str[:2], errors="coerce"), pd.to_numeric(times.str[2:], errors="coerce")
    time_ok = times.str.fullmatch(r"\d{4}") & hh.between(0, 23) & mm.between(0, 59)
    lat, lon = pd.to_numeric(raw.latitude, errors="coerce"), pd.to_numeric(raw.longitude, errors="coerce")
    sat = raw.satellite.str.upper().str.strip()
    version = raw.version.str.upper().str.strip()
    nrt = version.str.endswith("NRT")
    base_version = version.str.removesuffix("NRT")
    instrument = raw.get("instrument", pd.Series(spec["sensor"], index=raw.index)).str.upper().str.strip()
    if spec["sensor"] == "MODIS":
        quality = pd.to_numeric(raw.confidence, errors="coerce").between(0, 100)
    else:
        quality = raw.confidence.str.lower().str.strip().isin(["l", "n", "h"])
    checks = {
        "invalid_date": date_ok,
        "invalid_time": time_ok,
        "invalid_coordinates": lat.between(-85, 85) & lon.between(-180, 180),
        "outside_aoi": lat.between(south, north) & lon.between(west, east),
        "outside_period": dates.between(begin, finish),
        "wrong_satellite": sat.isin(spec["satellites"]),
        # FIRMS S-NPP archive exports may identify the instrument as SNPP.
        # Satellite is still checked independently; NOAA platforms cannot pass.
        "wrong_instrument": instrument.isin(["VIIRS", "SNPP"] if product == "VIIRS_SNPP_C2" else ["MODIS"]),
        "wrong_collection": base_version.isin(spec["standard"]),
        "nrt_not_allowed": ~nrt | allow_nrt,
        "invalid_sensor_confidence": quality,
    }
    keep = pd.Series(True, index=raw.index)
    for mask in checks.values():
        keep &= mask
    valid = raw.loc[keep].copy()
    checksum = hashlib.sha256(payload).hexdigest()
    safe_name = Path(filename.replace("\\", "/")).name
    if valid.empty:
        observations = pd.DataFrame(columns=EMPTY_COLUMNS)
    else:
        # A shared ordinal key preserves alignment through core's deduplication.
        instrument_original = valid.get("instrument", pd.Series("", index=valid.index)).copy()
        satellite_original = valid.satellite.copy()
        valid["instrument"] = spec["sensor"]
        valid["confidence"] = valid.confidence.str.strip().str.lower()
        observations = pd.concat([normalize_firms(group, spec["sensor"])
                                  for _, group in valid.groupby("version", sort=False)], ignore_index=True)
        meta = pd.DataFrame({
            "latitude": lat.loc[keep], "longitude": lon.loc[keep],
            "acquired_utc": dates.loc[keep] + pd.to_timedelta(hh.loc[keep], unit="h") + pd.to_timedelta(mm.loc[keep], unit="m"),
            "sensor": spec["sensor"], "satellite": sat.loc[keep],
            "version": valid.version,
            "acq_date_original": valid.acq_date, "acq_time_original": valid.acq_time,
            "instrument_original": instrument_original, "satellite_original": satellite_original,
            "source_row": valid.index + 2,
        })
        keys = ["latitude", "longitude", "acquired_utc", "sensor", "satellite", "version"]
        meta = meta.drop_duplicates(keys)
        observations = observations.merge(meta, on=keys, validate="one_to_one")
        for field in ("scan", "track", "type", "daynight"):
            if field in valid:
                lookup = valid.assign(source_row=valid.index + 2)[["source_row", field]]
                observations = observations.merge(lookup, on="source_row", validate="one_to_one")
        observations["product"] = product
        observations["collection"] = spec["collection"]
        observations["nominal_resolution_m"] = spec["nominal_resolution_m"]
        observations["processing"] = np_where_nrt(observations.version)
        observations["data_kind"] = data_kind
        observations["source_file"] = safe_name
        observations["source_sha256"] = checksum
    manifest = dict(
        filename=safe_name, sha256=checksum, bytes=len(payload), product=product,
        collection=spec["collection"], nominal_resolution_m=spec["nominal_resolution_m"],
        data_kind=data_kind, source_reference=ARCHIVE_URL,
        imported_utc=datetime.now(timezone.utc).isoformat(), requested_start=str(begin.date()),
        requested_end=str(finish.date()), bbox=[west, south, east, north], allow_nrt=allow_nrt,
        input_rows=len(raw), excluded_rows=int((~keep).sum()),
        duplicate_rows=int(keep.sum()) - len(observations), accepted_rows=len(observations),
        rejection_reasons={name: int((~mask).sum()) for name, mask in checks.items()},
        observed_start=str(observations.acquired_utc.min()) if len(observations) else None,
        observed_end=str(observations.acquired_utc.max()) if len(observations) else None,
        satellites=sorted(observations.satellite.unique().tolist()) if len(observations) else [],
        versions=sorted(observations.version.unique().tolist()) if len(observations) else [],
    )
    return HistoricalImport(observations, manifest)


def file_sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def discover_local_files(product: str, root: Path = Path("data/raw")) -> list[Path]:
    """Explicit archive naming in the root plus the pre-existing product folder."""
    if product not in PRODUCTS:
        raise ValueError("Producto histórico no admitido")
    folder, pattern = (("modis", "fire_archive_M-C61_*.csv") if product == "MODIS_C61"
                       else ("viirs_snpp", "fire_archive_SV-C2_*.csv"))
    return sorted(set(root.glob(pattern)) | set((root / folder).glob("*.csv")))


def import_file(path: Path, product: str, bbox=REGIONS["Amazonía peruana (AOI aproximada)"],
                start: str = OVERLAP_START, end: str | None = None, allow_nrt: bool = False,
                data_kind: str = "user_supplied_unverified", chunksize: int = 100000) -> HistoricalImport:
    """Bound memory on world CSVs while using the same row rules as import_csv.

    Hashes are of original bytes, before and after parsing. Chunk serialization
    is internal only; originals are never written. Source row offsets survive
    chunk boundaries. Global metadata and independent spatial counts are audited.
    """
    path = Path(path)
    if chunksize < 1:
        raise ValueError("chunksize debe ser positivo")
    checksum = file_sha256(path)
    west, south, east, north = validate_bbox(bbox)
    size = path.stat().st_size
    parts, manifests, offset = [], [], 0
    audit = dict(columns=[], global_dates={}, global_satellites={}, global_instruments={}, global_versions={},
                 global_confidence={}, global_type={}, aoi_rows_spatial_only=0, aoi_rows_before_quality=0,
                 latitude_min=None, latitude_max=None, longitude_min=None, longitude_max=None)
    finish = end or str(pd.Timestamp.now(tz="UTC").date())
    try:
        reader = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", chunksize=chunksize)
        for chunk in reader:
            chunk.columns = chunk.columns.str.strip().str.lower()
            audit["columns"] = list(chunk.columns)
            # The shared importer checks schema and row validity on every chunk.
            result = import_csv(chunk.to_csv(index=False).encode("utf-8"), path.name, product,
                                bbox, start, finish, allow_nrt, data_kind)
            if not result.observations.empty:
                result.observations["source_row"] += offset
                parts.append(result.observations)
            manifests.append(result.manifest)
            for field, label in [("acq_date", "global_dates"), ("satellite", "global_satellites"),
                                 ("instrument", "global_instruments"), ("version", "global_versions"),
                                 ("confidence", "global_confidence"), ("type", "global_type")]:
                if field in chunk:
                    for value, count in chunk[field].value_counts(dropna=False).items():
                        audit[label][str(value)] = audit[label].get(str(value), 0) + int(count)
            lat, lon = pd.to_numeric(chunk.latitude, errors="coerce"), pd.to_numeric(chunk.longitude, errors="coerce")
            spatial = lat.between(south, north) & lon.between(west, east)
            audit["aoi_rows_spatial_only"] += int(spatial.sum())
            dates = pd.to_datetime(chunk.acq_date, format="%Y-%m-%d", utc=True, errors="coerce")
            audit["aoi_rows_before_quality"] += int((spatial & dates.between(pd.Timestamp(start, tz="UTC"), pd.Timestamp(finish, tz="UTC"))).sum())
            for series, prefix in [(lat, "latitude"), (lon, "longitude")]:
                if series.notna().any():
                    lo, hi = float(series.min()), float(series.max())
                    audit[prefix+"_min"] = min(audit[prefix+"_min"], lo) if audit[prefix+"_min"] is not None else lo
                    audit[prefix+"_max"] = max(audit[prefix+"_max"], hi) if audit[prefix+"_max"] is not None else hi
            offset += len(chunk)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise ValueError("El archivo no es un CSV FIRMS válido con cabecera") from None
    if not manifests:
        return import_csv(path.read_bytes(), path.name, product, bbox, start, end, allow_nrt, data_kind)
    observations = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=EMPTY_COLUMNS)
    keys = ["latitude", "longitude", "acquired_utc", "sensor", "satellite", "version"]
    observations = observations.drop_duplicates(keys).reset_index(drop=True)
    if file_sha256(path) != checksum or path.stat().st_size != size:
        raise ValueError("El archivo original cambió durante la lectura; resultado descartado")
    if not observations.empty:
        observations["source_sha256"] = checksum
    manifest = manifests[0].copy()
    manifest.update(sha256=checksum, bytes=size, input_rows=offset,
                    accepted_rows=len(observations), excluded_rows=sum(m["excluded_rows"] for m in manifests),
                    duplicate_rows=offset-sum(m["excluded_rows"] for m in manifests)-len(observations),
                    rejection_reasons={key: sum(m["rejection_reasons"][key] for m in manifests) for key in manifests[0]["rejection_reasons"]},
                    observed_start=str(observations.acquired_utc.min()) if len(observations) else None,
                    observed_end=str(observations.acquired_utc.max()) if len(observations) else None,
                    satellites=sorted(observations.satellite.unique().tolist()) if len(observations) else [],
                    versions=sorted(observations.version.unique().tolist()) if len(observations) else [],
                    original_bytes_unchanged=True, chunksize=chunksize, input_audit=audit,
                    provenance_status="archivo aportado como original NASA por el usuario; metadatos consistentes no certifican descarga")
    return HistoricalImport(observations, manifest)


def np_where_nrt(versions):
    # Keep processing label separate from collection; no merging NRT with SP.
    return versions.str.upper().str.endswith("NRT").map({True: "NRT", False: "SP"})


def combine_imports(imports: list[HistoricalImport]) -> tuple[pd.DataFrame, dict]:
    frames = [item.observations for item in imports if not item.observations.empty]
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=EMPTY_COLUMNS)
    before = len(data)
    # Retain distinct versions/products: they must not be silently treated as one.
    keys = ["latitude", "longitude", "acquired_utc", "sensor", "satellite", "product", "version", "data_kind"]
    data = data.drop_duplicates(keys).reset_index(drop=True)
    return data, dict(files=[i.manifest for i in imports], cross_file_duplicates=before-len(data), accepted_rows=len(data))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Importar CSV históricos declarados FIRMS; no certifica autenticidad")
    parser.add_argument("--modis", type=Path, nargs="*", default=[])
    parser.add_argument("--viirs", type=Path, nargs="*", default=[])
    parser.add_argument("--bbox", nargs=4, type=float, default=list(REGIONS.values())[0])
    parser.add_argument("--start", default=OVERLAP_START)
    parser.add_argument("--end")
    parser.add_argument("--allow-nrt", action="store_true")
    parser.add_argument("--processing", choices=["SP", "NRT"], default="SP", help="Cohorte de análisis; no mezcla SP y NRT")
    parser.add_argument("--synthetic", action="store_true", help="Solo fixtures: no son observaciones NASA")
    parser.add_argument("--modis-min", type=int, choices=range(101), default=0)
    parser.add_argument("--exclude-viirs-low", action="store_true")
    parser.add_argument("--cell-m", type=int, default=1000)
    parser.add_argument("--tolerance-minutes", type=int, default=60)
    parser.add_argument("--sensitivity", action="store_true", help="Diagnóstico adicional 1/2/5 km × ±30/60/90 min")
    parser.add_argument("--output", type=Path, required=True, help="Directorio NUEVO; no sobrescribe resultados")
    args = parser.parse_args(argv)
    if not args.modis and not args.viirs:
        parser.error("Indica al menos un CSV --modis o --viirs")
    imports = []
    try:
        for product, paths in (("MODIS_C61", args.modis), ("VIIRS_SNPP_C2", args.viirs)):
            for path in paths:
                imports.append(import_file(path, product, args.bbox, args.start, args.end,
                                          args.allow_nrt, "synthetic" if args.synthetic else "user_supplied_unverified"))
        data, manifest = combine_imports(imports)
        cohort = data.loc[data.processing == args.processing] if len(data) else data
        filtered = confidence_filter(cohort, args.modis_min, args.exclude_viirs_low) if len(cohort) else cohort
        from firesync.calendar import sensor_calendar, experimental_calendar, daily_sensor_activity
        from firesync.calibration import diagnose_overlap
        calendar = sensor_calendar(filtered, args.cell_m)
        diagnosis = diagnose_overlap(filtered, args.cell_m, args.tolerance_minutes)
        manifest.update(schema_version=1, cell_m=args.cell_m, tolerance_minutes=args.tolerance_minutes,
                        modis_min=args.modis_min, exclude_viirs_low=args.exclude_viirs_low,
                        analysis_processing=args.processing,
                        after_confidence_filter=len(filtered), region="bbox aproximada; no límite oficial",
                        method_version="firesync-ai-0.3.0", python_version=platform.python_version(),
                        dependencies={name: version(name) for name in ["pandas", "numpy", "pyproj", "requests"]},
                        bootstrap_samples=1000, bootstrap_seed=42, min_train_days=20,
                        min_validation_days=10, min_matches_per_partition=20,
                        calibration_status="experimental; cobertura no verificada",
                        observation_kind="synthetic" if args.synthetic else "user_supplied_unverified")
        args.output.mkdir(parents=True, exist_ok=False)
        data.to_csv(args.output / "observations.csv", index=False)
        calendar.to_csv(args.output / "calendar.csv", index=False)
        daily_sensor_activity(filtered, args.cell_m).to_csv(args.output / "daily_comparison.csv", index=False)
        diagnosis.monthly.to_csv(args.output / "overlap_monthly.csv", index=False)
        diagnosis.periods.to_csv(args.output / "overlap_pairs.csv", index=False)
        diagnosis.normalization.to_csv(args.output / "evaluation.csv", index=False)
        experimental_calendar(diagnosis.normalization).to_csv(args.output / "calendar_experimental.csv", index=False)
        if args.sensitivity:
            rows = []
            for grid in (1000, 2000, 5000):
                for tolerance in (30, 60, 90):
                    analysis = diagnose_overlap(filtered, grid, tolerance)
                    table = analysis.monthly.assign(cell_m=grid, tolerance_minutes=tolerance,
                                                    unpaired_acquisitions=analysis.unpaired_acquisitions)
                    rows.append(table)
            pd.concat(rows, ignore_index=True).to_csv(args.output / "sensitivity.csv", index=False)
        manifest["sensitivity_requested"] = args.sensitivity
        manifest["unpaired_acquisitions"] = diagnosis.unpaired_acquisitions
        manifest["output_sha256"] = {path.name: file_sha256(path) for path in args.output.glob("*.csv")}
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(dict(rows=len(data), paired_periods=len(diagnosis.periods), output=str(args.output),
                          data_kind=manifest["observation_kind"]), ensure_ascii=True))


if __name__ == "__main__":
    main()
