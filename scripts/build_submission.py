"""Create a reviewed source-only archive: no observations, credentials or venvs."""
import hashlib
import json
from pathlib import Path
import zipfile

from submission_audit import ROOT, audit


def main():
    report, files = audit()
    if report["exclusion_failures"] or report["possible_leaks"] or report["tracked_ignored_files"]:
        raise SystemExit("El control de publicación encontró archivos a revisar; no se creó el ZIP")
    destination = ROOT / "dist/FireSyncAI_submission.zip"
    destination.parent.mkdir(exist_ok=True)
    allowed_suffixes = {".py", ".ps1", ".md", ".toml", ".txt"}
    included = []
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = path.relative_to(ROOT).as_posix()
            if (path.suffix in allowed_suffixes or name in {".env.example", ".gitignore"}
                    or name in {"data/demo_modis.csv", "data/demo_viirs.csv"}):
                archive.write(path, "FireSyncAI/"+name)
                included.append(name)
    result = dict(archive=str(destination.relative_to(ROOT)), bytes=destination.stat().st_size,
                  sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), files=included,
                  data_note="Código y demostración sintética rotulada. Los originales y la AOI real deben facilitarse por separado.")
    (destination.parent / "submission_manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "files"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
