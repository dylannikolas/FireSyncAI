"""Optional offline recovery of pure-Python wheels already in the local pip cache.

Does not download or rebuild packages. Scientific CPython extensions must be
installed separately for the target Python; cp311 binaries cannot serve cp312.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".offline-wheels"))
    parser.add_argument("--packages", nargs="+", default=["pytest", "pluggy", "iniconfig", "plotly"])
    args = parser.parse_args()
    cache = Path(subprocess.check_output([sys.executable, "-m", "pip", "cache", "dir"], text=True).strip())
    args.output.mkdir(parents=True, exist_ok=True)
    wanted = {p.lower().replace("-", "_") for p in args.packages}
    found = set()
    for path in cache.rglob("*.body"):
        try:
            with zipfile.ZipFile(path) as archive:
                metadata = next((n for n in archive.namelist() if n.endswith(".dist-info/METADATA")), "")
                if not metadata:
                    continue
                root = metadata.split("/")[0].removesuffix(".dist-info")
                name = root.rsplit("-", 1)[0].lower().replace("-", "_")
                if name not in wanted:
                    continue
                wheel = archive.read(root + ".dist-info/WHEEL").decode("utf-8")
                if "Tag: py3-none-any" not in wheel or "Root-Is-Purelib: true" not in wheel:
                    continue
                destination = args.output / (root + "-py3-none-any.whl")
                shutil.copyfile(path, destination)
                found.add(name)
                print(destination.name)
        except (zipfile.BadZipFile, OSError, KeyError):
            continue
    missing = wanted - found
    if missing:
        print("No disponibles en cache: " + ", ".join(sorted(missing)))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
