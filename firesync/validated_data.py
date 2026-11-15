"""Load an explicitly selected processed observational bundle, with checksums.

Checksums detect local changes; they are not NASA signatures or truth labels.
"""
import json
from pathlib import Path

import pandas as pd

from firesync.history import HistoricalImport, file_sha256

REAL_AUGUST_BUNDLE = Path("data/processed/real_2024_08")


def load_observational_bundle(folder: Path, raw_root: Path = Path("data/raw")) -> list[HistoricalImport]:
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("observation_kind") != "user_supplied_unverified":
        raise ValueError("Esta vista requiere observaciones aportadas, no datos sintéticos ni estimaciones")
    checksums = manifest.get("output_sha256", {})
    if "observations.csv" not in checksums:
        raise ValueError("Manifiesto sin checksum de observaciones; vuelve a importar")
    for name, checksum in checksums.items():
        if Path(name).name != name or not name.endswith(".csv"):
            raise ValueError("Nombre de salida inválido en manifiesto")
        if file_sha256(folder / name) != checksum:
            raise ValueError(f"Salida modificada: {name}; vuelve a importar")
    records = pd.read_csv(folder / "observations.csv", dtype={"version": str, "confidence": str,
                          "collection": str, "acq_time_original": str, "acq_date_original": str})
    records["acquired_utc"] = pd.to_datetime(records.acquired_utc, utc=True, errors="raise")
    records["date"] = records.acquired_utc.dt.date
    if len(records) != manifest["accepted_rows"] or not records.data_kind.eq("user_supplied_unverified").all():
        raise ValueError("Conteo o procedencia incompatible con manifiesto")
    result = []
    for source in manifest["files"]:
        name = source["filename"]
        if Path(name).name != name:
            raise ValueError("Nombre de entrada inválido en manifiesto")
        path = raw_root / name
        if not path.is_file() or file_sha256(path) != source["sha256"]:
            raise ValueError(f"Original ausente o modificado: {name}")
        subset = records.loc[records.source_file == name].copy()
        if len(subset) != source["accepted_rows"] or not subset.source_sha256.eq(source["sha256"]).all():
            raise ValueError("Procedencia de filas incompatible con original")
        result.append(HistoricalImport(subset, source))
    if sum(len(item.observations) for item in result) != len(records):
        raise ValueError("Filas sin archivo de origen declarado")
    return result
