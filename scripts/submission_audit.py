"""Check release exclusions and likely embedded secrets without printing values.

An isolated temporary Git repository checks the project's actual ignore rules;
the project's index is inspected only if this folder is an actual repository.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,})\b"),
    re.compile(r'''(?im)^\s*(?:API_KEY|SECRET_KEY|ACCESS_TOKEN|AWS_SECRET_ACCESS_KEY)\s*=\s*["']?[A-Za-z0-9_+/=-]{20,}["']?\s*$'''),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"/api/area/csv/[0-9a-fA-F]{32}/"),
    re.compile(r'''(?im)^\s*FIRMS_MAP_KEY\s*=\s*["']?[a-zA-Z0-9_-]{20,}["']?\s*$'''),
]


def source_files():
    excluded = {".git", "__pycache__", ".pytest_cache", ".offline-wheels", "reports", "dist", "build", "raw", "processed"}
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in excluded and not d.startswith(".venv") and not d.endswith(".egg-info")]
        for name in files:
            yield Path(folder) / name


def ignored_paths(paths):
    if not paths:
        return set()
    with tempfile.TemporaryDirectory(prefix="firesync-ignore-") as temp:
        subprocess.run(["git", "init", "-q", temp], check=True, capture_output=True)
        shutil.copyfile(ROOT / ".gitignore", Path(temp) / ".gitignore")
        result = subprocess.run(["git", "-C", temp, "check-ignore", "--no-index", "-z", "--stdin"],
                                input=("\0".join(paths)+"\0").encode("utf-8"), capture_output=True)
        if result.returncode not in (0, 1):
            raise RuntimeError("No se pudieron comprobar las exclusiones Git")
        return set(result.stdout.decode("utf-8").strip("\0").split("\0")) - {""}


def audit():
    files = list(source_files())
    relative = [p.relative_to(ROOT).as_posix() for p in files]
    probes = ["data/raw/fire_archive_M-C61_851101.csv", "data/raw/fire_archive_SV-C2_851102.csv",
              "data/processed/real_2024_08/observations.csv", "fire_archive_accidental.csv", "DL_FIRE_example.zip",
              ".env", ".env.production", ".streamlit/secrets.toml", "private.pem", "private.key", "dist/submission.zip",
              ".venv-custom/pyvenv.cfg", "archive.zip", "reports/browser/History", "credentials.json"]
    ignored = ignored_paths(relative + probes)
    failures = [p for p in probes if p not in ignored]
    public = ["videos/FireSyncAI_demo_30s.mp4", "data/demo_modis.csv", "data/demo_viirs.csv", ".env.example"]
    failures.extend(sorted(ignored_paths(public)))
    leaks = []
    eligible = [p for p, name in zip(files, relative) if name not in ignored]
    for path in eligible:
        if path.stat().st_size > 5_000_000:
            leaks.append(dict(file=path.relative_to(ROOT).as_posix(), kind="unexpected_large_file"))
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (UnicodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                leaks.append(dict(file=path.relative_to(ROOT).as_posix(), kind="possible_secret"))
                break
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True, text=True)
    tracked_sensitive = None
    if repo.returncode == 0:
        tracked = [p for p in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0") if p]
        tracked_sensitive = sorted(set(tracked) & ignored_paths(tracked))
    result = dict(ignore_probes=len(probes), exclusion_failures=failures, scanned_files=len(eligible),
                  possible_leaks=leaks, git_index_available=repo.returncode == 0,
                  tracked_ignored_files=tracked_sensitive,
                  note="Escaneo heurístico; valores secretos nunca se muestran. Sin .git no se puede auditar índice/historial.")
    return result, eligible


if __name__ == "__main__":
    report, _ = audit()
    print(json.dumps(report, indent=2, ensure_ascii=True))
    raise SystemExit(bool(report["exclusion_failures"] or report["possible_leaks"] or report["tracked_ignored_files"]))
