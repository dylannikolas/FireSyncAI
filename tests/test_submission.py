"""Release checks: real ignore rules and redaction of a deliberately fake key."""
from pathlib import Path

from scripts import submission_audit


def test_empty_index_and_public_video_are_supported():
    assert submission_audit.ignored_paths([]) == set()
    assert not submission_audit.ignored_paths(["videos/FireSyncAI_demo_30s.mp4", "data/demo_modis.csv", "data/demo_viirs.csv"])


def test_release_excludes_world_archives_and_secrets_but_keeps_public_config():
    paths = ["fire_archive_accidental.csv", "data/raw/world.csv", "data/processed/observations.csv",
             ".env.production", ".streamlit/secrets.toml", "dist/submission.zip", ".env.example", ".streamlit/config.toml"]
    ignored = submission_audit.ignored_paths(paths)
    assert set(paths[:6]).issubset(ignored)
    assert not set(paths[6:]) & ignored


def test_release_reports_fake_embedded_key_without_exposing_value(tmp_path, monkeypatch):
    import json
    original_root = submission_audit.ROOT
    (tmp_path / ".gitignore").write_bytes((original_root / ".gitignore").read_bytes())
    fake = "a" * 32  # Artificial pattern, never an actual credential.
    (tmp_path / "accidental.py").write_text("FIRMS_MAP_KEY=" + fake)
    monkeypatch.setattr(submission_audit, "ROOT", tmp_path)
    result, _ = submission_audit.audit()
    assert result["possible_leaks"] == [dict(file="accidental.py", kind="possible_secret")]
    assert fake not in json.dumps(result)
