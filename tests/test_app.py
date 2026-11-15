"""Exercise the dashboard on the existing explicitly synthetic demonstration."""
from streamlit.testing.v1 import AppTest
from pathlib import Path
import json
import shutil
import pandas as pd


def test_validation_tab_preserves_basic_metrics_and_handles_empty_aoi():
    app = AppTest.from_file("app.py", default_timeout=60).run()
    assert not app.exception
    assert len(app.tabs) == 5
    assert app.tabs[-1].label == "Validación MODIS↔VIIRS"
    metrics = [(m.label, m.value) for m in app.metric]
    assert len(metrics) == 4
    assert any("SINTÉTICOS" in warning.value for warning in app.warning)
    next(c for c in app.checkbox if c.label == "Recortar una AOI para esta validación").check().run()
    assert not app.exception
    for field in app.number_input:
        if field.label == "AOI oeste":
            field.set_value(0.)
        elif field.label == "AOI este":
            field.set_value(1.)
    app.run()
    assert not app.exception
    assert any("insuficiente información" in message.value for message in app.info)
    assert metrics == [(m.label, m.value) for m in app.metric]


def test_historical_manual_pipeline_and_experimental_calendar_with_artificial_fixtures(tmp_path, monkeypatch):
    """Local files below are ARTIFICIAL; metadata consistency is not authenticity."""
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "data", tmp_path / "data", ignore=shutil.ignore_patterns("raw", "processed"))
    for product, directory, sensor, sat, version, confidence in [
        ("MODIS_C61", "modis", "MODIS", "T", "6.1", "80"),
        ("VIIRS_SNPP_C2", "viirs_snpp", "VIIRS", "N", "2", "n"),
    ]:
        folder = tmp_path / "data/raw" / directory
        folder.mkdir(parents=True)
        rows = [dict(latitude=-9.3, longitude=-74., acq_date=f"{year}-08-{day:02d}", acq_time="1200",
                     instrument=sensor, satellite=sat, version=version, confidence=confidence)
                for year in (2022, 2023, 2024) for day in range(1, 21)]
        pd.DataFrame(rows).to_csv(folder / f"ARTIFICIAL_{product}.csv", index=False)
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(root / "app.py"), default_timeout=60).run()
    app.radio[0].set_value("Históricos MODIS C6.1 / S-NPP C2").run()
    assert not app.exception
    assert app.metric[0].value == "120"
    assert any("procedencia no autenticada" in caption.value for caption in app.caption)
    next(s for s in app.selectbox if s.label == "Serie del calendario").select("Reconciliada experimental (celdas-periodo)").run()
    assert not app.exception
    assert any("Solo se muestra VIIRS reconciliado" in c.value for c in app.caption)
    # One reserved August with factor 1 is exposed; training years are not plotted as harmonized observations.
    assert any("Exportar calendario experimental reservado" == b.label for b in app.get("download_button"))


def test_calendar_handles_no_selected_years():
    app = AppTest.from_file("app.py", default_timeout=60).run()
    spec = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert spec["layout"]["yaxis"]["type"] == "category"
    assert spec["data"][0]["zmin"] == 0
    next(s for s in app.multiselect if s.label == "Años del calendario").set_value([]).run()
    assert not app.exception
    assert any("Sin información suficiente" in message.value for message in app.info)


def test_missing_real_bundle_shows_one_error_without_synthetic_fallback(monkeypatch):
    import firesync.validated_data
    def missing(*args, **kwargs):
        raise FileNotFoundError("Original ausente (fixture de error)")
    monkeypatch.setattr(firesync.validated_data, "load_observational_bundle", missing)
    app = AppTest.from_file("app.py", default_timeout=60)
    app.query_params["source"] = "real"
    app.run()
    assert not app.exception and len(app.error) == 1
    assert "No se pudo verificar" in app.error[0].value
    assert len(app.metric) == 0
    assert not any("DATOS SINTÉTICOS" in w.value for w in app.warning)
