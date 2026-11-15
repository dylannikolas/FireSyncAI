"""FireSync AI: interactive NASA FIRMS spatial/temporal exploratory dashboard."""
from __future__ import annotations
import io
import os
import json
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from firesync.core import normalize_firms, confidence_filter, aggregate_cells, daily_activity, monthly_activity, historical_anomalies
from firesync.nasa import fetch_recent_area, fetch_public_24h, fetch_historical_area, SOURCES
from firesync.calibration import diagnose_overlap
from firesync.history import import_csv, import_file, discover_local_files, combine_imports, REGIONS, OVERLAP_START
from firesync.calendar import sensor_calendar, experimental_calendar, daily_sensor_activity
from firesync.validated_data import load_observational_bundle, REAL_AUGUST_BUNDLE

MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


@st.cache_data(show_spinner="Validando archivo histórico por bloques…")
def load_local_history(path, product, bbox, start, end, allow_nrt, mtime_ns, size_bytes):
    # mtime/size are cache keys; original-byte hashes are verified on cache misses.
    return import_file(Path(path), product, bbox, start, end, allow_nrt)

st.set_page_config(page_title="FireSync AI · NASA Space Apps", page_icon="🔥", layout="wide")
st.markdown("""<style>
.main h1 { letter-spacing: -.04em; } div[data-testid="stMetric"] {border: 1px solid #293b49;border-radius:12px;padding:13px;}
</style>""", unsafe_allow_html=True)
st.title("🔥 FireSync AI")
st.caption("NASA Space Apps Challenge 2026 · Actividad térmica MODIS–VIIRS con trazabilidad")
st.markdown("**Del píxel de calor a una comparación transparente.** MODIS y VIIRS observan a distintas resoluciones y horarios. FireSync AI conserva su origen y los compara sobre una cuadrícula y un calendario comunes.")
st.info("Análisis exploratorio de **detecciones de calor**, no incendios únicos ni predicciones. La agregación no corrige por sí sola sensibilidad, nubes o cobertura; la calibración científica sigue sin validarse.")

with st.sidebar:
    st.header("🛰️ Origen de datos")
    origin = st.radio("Selecciona fuente", ["Demostración simulada", "Cargar CSV históricos", "NASA FIRMS · CSV público 24h", "NASA FIRMS · recientes", "Históricos MODIS C6.1 / S-NPP C2", "NASA FIRMS · histórico API", "Observaciones FIRMS · agosto 2024 (AOI)"], index=6 if st.query_params.get("source") == "real" else 0)
    raw_frames: list[tuple[pd.DataFrame, str]] = []
    historical_imports = []
    historical_mode = origin in ["Históricos MODIS C6.1 / S-NPP C2", "NASA FIRMS · histórico API", "Observaciones FIRMS · agosto 2024 (AOI)"]
    sample_flag = origin == "Demostración simulada"
    if origin == "Demostración simulada":
        st.warning("Datos artificiales para probar la aplicación; NO son observaciones NASA.")
        raw_frames = [(pd.read_csv("data/demo_modis.csv"), "MODIS"), (pd.read_csv("data/demo_viirs.csv"), "VIIRS")]
    elif origin == "Cargar CSV históricos":
        uploads = st.file_uploader("CSV originales de NASA FIRMS", type=["csv"], accept_multiple_files=True)
        for upload in uploads or []:
            try:
                raw_frames.append((pd.read_csv(io.BytesIO(upload.getvalue())), upload.name))
            except (ValueError, UnicodeDecodeError):
                st.error(f"CSV ilegible: {upload.name}")
        st.caption("Carga genérica: procedencia suministrada por el usuario, no autenticada. Para validar colección y plataforma usa Históricos MODIS C6.1 / S-NPP C2.")
    elif origin == "Observaciones FIRMS · agosto 2024 (AOI)":
        st.info("Observaciones FIRMS aportadas como originales NASA por el usuario. AOI Amazonía peruana, 1–31 agosto 2024; SP, sin datos sintéticos. Se verifican hashes de originales y resultados.")
        st.caption("Celda inicial 1000 m y filtros de confianza sin exclusión. Un mes permite concordancia exploratoria, no calibración por años.")
        try:
            historical_imports = load_observational_bundle(REAL_AUGUST_BUNDLE)
        except (ValueError, OSError, KeyError) as exc:
            st.error(f"No se pudo verificar la AOI procesada: {exc}. Ejecuta la importación indicada en REAL_DATA_VALIDATION.md.")
            st.stop()
    elif historical_mode:
        region = st.selectbox("Región histórica", list(REGIONS))
        historical_bbox = REGIONS[region]
        st.caption(f"Caja W,S,E,N: {historical_bbox}. Región aproximada, no límite administrativo ni máscara del bioma.")
        api_history = origin == "NASA FIRMS · histórico API"
        hs = st.date_input("Inicio histórico UTC", value=date(2023, 8, 1) if api_history else date.fromisoformat(OVERLAP_START), min_value=date.fromisoformat(OVERLAP_START))
        he = st.date_input("Fin histórico UTC", value=date(2023, 8, 31) if api_history else date.today(), min_value=date.fromisoformat(OVERLAP_START))
        historical_nrt = st.checkbox("Admitir NRT explícitamente (no mezclar con SP en evaluación)", value=False)
        if origin == "Históricos MODIS C6.1 / S-NPP C2":
            st.info("Archivos oficiales del archivo FIRMS: MODIS Terra/Aqua C6.1 y VIIRS S-NPP C2. La validación de metadatos no certifica autenticidad del archivo local.")
            for product, label, directory in [("MODIS_C61", "CSV MODIS Terra/Aqua C6.1", "modis"), ("VIIRS_SNPP_C2", "CSV VIIRS S-NPP C2 (375 m)", "viirs_snpp")]:
                uploads = st.file_uploader(label, type=["csv"], accept_multiple_files=True, key=product)
                inputs = [(u.name, u.getvalue()) for u in uploads or []]
                local = discover_local_files(product)
                labels = {str(p.relative_to("data/raw")): p for p in local}
                selected = st.multiselect(f"Archivos locales {product}", list(labels), default=list(labels))
                for selection in selected:
                    path = labels[selection]
                    try:
                        stat = path.stat()
                        historical_imports.append(load_local_history(str(path.resolve()), product, historical_bbox, str(hs), str(he), historical_nrt, stat.st_mtime_ns, stat.st_size))
                    except (ValueError, OSError) as exc:
                        st.error(f"{path.name}: {exc}")
                for name, payload in inputs:
                    try:
                        historical_imports.append(import_csv(payload, name, product, historical_bbox, str(hs), str(he), historical_nrt))
                    except ValueError as exc:
                        st.error(f"{name}: {exc}")
        else:
            st.caption("Consulta SP de hasta 31 días en bloques ≤5 días. Disponibilidad histórica sujeta a FIRMS; para varios años usa CSV oficiales.")
            hkey = st.text_input("MAP_KEY histórica (privada)", type="password", value=os.getenv("FIRMS_MAP_KEY", ""))
            if st.button("Consultar subconjunto histórico SP"):
                st.session_state.pop("historical_api_result", None)
                fetched_history = []
                try:
                    for product in ("MODIS_C61", "VIIRS_SNPP_C2"):
                        table = fetch_historical_area(hkey, product, historical_bbox, str(hs), str(he))
                        imported_api = import_csv(table.to_csv(index=False).encode("utf-8"), f"{product}_{hs}_{he}.csv", product,
                                                  historical_bbox, str(hs), str(he), data_kind="nasa_api")
                        imported_api.manifest.update(source_reference="https://firms.modaps.eosdis.nasa.gov/api/area/",
                                                     api_requests=table.attrs.get("api_requests", []),
                                                     checksum_scope="CSV serializado; hashes de texto de respuestas en api_requests")
                        fetched_history.append(imported_api)
                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.session_state["historical_api_result"] = ((region, str(hs), str(he)), fetched_history)
            stored = st.session_state.get("historical_api_result")
            if stored and stored[0] == (region, str(hs), str(he)):
                historical_imports = stored[1]
        if historical_imports:
            st.download_button("Exportar manifiestos de importación", json.dumps([i.manifest for i in historical_imports], indent=2, ensure_ascii=False).encode("utf-8"), "import_manifests.json", "application/json")
            st.caption(f"Archivos: {len(historical_imports)}. Filas excluidas: {sum(i.manifest['excluded_rows'] for i in historical_imports)}. Consulta motivos en los manifiestos.")
    elif origin == "NASA FIRMS · CSV público 24h":
        st.caption("Descarga archivos globales públicos de NASA y recórtalos al área. No requiere MAP_KEY; depende de la disponibilidad de los servidores FIRMS.")
        west = st.number_input("Oeste", value=-76.5, min_value=-180., max_value=180., key="public_w")
        south = st.number_input("Sur", value=-12.5, min_value=-85., max_value=85., key="public_s")
        east = st.number_input("Este", value=-72.0, min_value=-180., max_value=180., key="public_e")
        north = st.number_input("Norte", value=-7.0, min_value=-85., max_value=85., key="public_n")
        public_sources = st.multiselect("Fuentes públicas", ["MODIS", "VIIRS_SNPP", "VIIRS_NOAA20"], default=["MODIS", "VIIRS_SNPP"])
        if st.button("Descargar datos reales (24h)", type="primary", use_container_width=True):
            downloaded = []
            with st.spinner("Descargando datos FIRMS públicos..."):
                for source in public_sources:
                    try:
                        subdf = fetch_public_24h(source, (west, south, east, north))
                        if not subdf.empty:
                            downloaded.append((subdf, source))
                    except (RuntimeError, ValueError) as error:
                        st.error(f"{source}: {error}")
                st.session_state["firms_public_frames"] = downloaded
        raw_frames = st.session_state.get("firms_public_frames", [])
    else:
        st.caption("Obtén tu MAP_KEY gratuita en https://firms.modaps.eosdis.nasa.gov/api/map_key")
        key = st.text_input("MAP_KEY (privada)", type="password", value=os.getenv("FIRMS_MAP_KEY", ""))
        n_days = st.select_slider("Últimos días", options=[1,2,3,4,5], value=3)
        st.markdown("**Coordenadas del área** (W,S,E,N)")
        west = st.number_input("Oeste", value=-76.5, min_value=-180., max_value=180.)
        south = st.number_input("Sur", value=-12.5, min_value=-85., max_value=85.)
        east = st.number_input("Este", value=-72.0, min_value=-180., max_value=180.)
        north = st.number_input("Norte", value=-7.0, min_value=-85., max_value=85.)
        source_opts = st.multiselect("Satélites", list(SOURCES), default=["MODIS_NRT", "VIIRS_NOAA20_NRT"])
        if st.button("Consultar NASA FIRMS", type="primary", use_container_width=True):
            if not key:
                st.error("Introduce una MAP_KEY válida; no la compartas en el repositorio.")
            elif not source_opts:
                st.error("Selecciona por lo menos una fuente.")
            else:
                with st.spinner("Recuperando detecciones NASA..."):
                    fetched = []
                    for source in source_opts:
                        try:
                            result = fetch_recent_area(key, source, (west, south, east, north), n_days)
                            if not result.empty:
                                fetched.append((result, source))
                        except (RuntimeError, ValueError) as error:
                            st.error(f"{source}: {error}")
                    st.session_state["firms_live_frames"] = fetched
        raw_frames = st.session_state.get("firms_live_frames", [])
    st.divider()
    st.header("⚙️ Metodología")
    cell_m = st.selectbox("Tamaño de celda de igual área", [1000, 2000, 5000], index=0, format_func=lambda x: f"{x:,} m".replace(",", " "))
    modis_min = st.slider("Confianza MODIS mínima (%)", 0, 100, 0, 10)
    drop_viirs_low = st.checkbox("Excluir VIIRS confianza baja (l)", value=False)

if not raw_frames and not historical_imports:
    st.warning("Sube archivos CSV de MODIS/VIIRS o realiza una consulta a NASA.")
    st.stop()

try:
    if historical_mode:
        normalized, import_manifest = combine_imports(historical_imports)
    else:
        normalized = pd.concat([normalize_firms(df, hint) for df, hint in raw_frames], ignore_index=True)
    dedup_keys = ["latitude", "longitude", "acquired_utc", "sensor", "satellite"]
    normalized = normalized.drop_duplicates(subset=dedup_keys + (["product", "version", "data_kind"] if historical_mode else []))
    if historical_mode and not normalized.empty:
        with st.sidebar:
            processing_options = sorted(normalized.processing.unique())
            processing = st.selectbox("Procesamiento para análisis", processing_options,
                                      index=processing_options.index("SP") if "SP" in processing_options else 0)
        normalized = normalized.loc[normalized.processing == processing].copy()
    observations = confidence_filter(normalized, modis_min, drop_viirs_low)
    cells = aggregate_cells(observations, cell_m)
except (ValueError, KeyError, TypeError) as exc:
    st.error(f"Error procesando los CSV: {exc}")
    st.stop()

if cells.empty:
    st.warning("Sin observaciones después de aplicar los filtros de calidad.")
    st.stop()

first, last = min(cells["date"]), max(cells["date"])
with st.container():
    source_label = 'SINTÉTICA / SIMULADA' if sample_flag else ('FIRMS observado: originales aportados por usuario, metadatos y hashes verificados' if origin == 'Observaciones FIRMS · agosto 2024 (AOI)' else ('CSV del usuario: procedencia no autenticada' if origin in ['Cargar CSV históricos', 'Históricos MODIS C6.1 / S-NPP C2'] else 'NASA FIRMS (API/descarga)'))
    st.caption(f"**Fuente:** {source_label}  ·  **Periodo observado:** {first} a {last}  ·  **Zona horaria:** UTC  ·  **Métrica:** celdas-día activas")
    if sample_flag:
        st.warning("DATOS SINTÉTICOS · Demostración de interfaz. Estos registros no son observaciones NASA ni evidencia de calibración.")
    elif origin == "Observaciones FIRMS · agosto 2024 (AOI)":
        st.success("DATOS OBSERVADOS · Amazonía peruana, agosto 2024 · MODIS Terra/Aqua C6.1 + VIIRS S-NPP C2 · SP · Originales y resultados verificados por hash.")

k1,k2,k3,k4 = st.columns(4)
k1.metric("Detecciones procesadas", f"{len(observations):,}")
k2.metric("Celdas-día activas", f"{len(cells):,}")
k3.metric("MODIS · detecciones", f"{int(observations.sensor.eq('MODIS').sum()):,}")
k4.metric("VIIRS · detecciones", f"{int(observations.sensor.eq('VIIRS').sum()):,}")

st.caption(f"{int((cells.modis_seen & cells.viirs_seen).sum()):,} celdas-día registradas por ambos sensores. La unión observada combina celdas del mismo día; no identifica incendios independientes ni corrige detectabilidad.")
t1, t2, t3, t4, t5 = st.tabs(["🗺️ Mapa de actividad", "📅 Calendario histórico", "📈 Anomalías exploratorias", "🔬 Datos y metodología", "Validación MODIS↔VIIRS"])

with t1:
    st.subheader("Actividad térmica observada por celda y día")
    if first == last:
        selected_start, selected_end = first, last
        st.caption("Una sola fecha disponible.")
    else:
        initial_days = 6 if origin == "Observaciones FIRMS · agosto 2024 (AOI)" else 60
        date_range = st.slider("Intervalo para el mapa", min_value=first, max_value=last, value=(max(first, last - timedelta(days=initial_days)), last))
        selected_start, selected_end = date_range
    mapped = cells.loc[(cells["date"] >= selected_start) & (cells["date"] <= selected_end)].copy()
    if len(mapped) > 10000:
        st.warning("El mapa muestra las primeras 10 000 celdas del intervalo. Descarga el CSV para analizar el conjunto completo.")
        mapped = mapped.head(10000)
    if not mapped.empty:
        mapped["source_type"] = np.select([mapped.modis_seen & mapped.viirs_seen, mapped.viirs_seen], ["MODIS + VIIRS", "VIIRS"], default="MODIS")
        colors = {"MODIS + VIIRS": [147, 51, 234, 185], "VIIRS": [249, 115, 22, 170], "MODIS": [14, 165, 233, 170]}
        mapped["marker_color"] = mapped["source_type"].map(colors)
        mapped["date"] = mapped["date"].astype(str)
        layer = pdk.Layer("ScatterplotLayer", mapped, get_position="[longitude, latitude]", get_radius=max(150, cell_m * .45), radius_min_pixels=2, get_fill_color="marker_color", pickable=True, opacity=.75, stroked=False)
        view = pdk.ViewState(latitude=float(mapped.latitude.mean()), longitude=float(mapped.longitude.mean()), zoom=6 if origin == "Observaciones FIRMS · agosto 2024 (AOI)" else 5, pitch=0)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip={"html": "<b>{date}</b><br/>Origen: {source_type}<br/>Detecciones: {raw_count}<br/>Satélites: {satellites}"}), use_container_width=True)
        st.caption("🟣 Ambos sensores · 🟠 VIIRS · 🔵 MODIS. Cada punto representa una celda-día observada; colores y conteos no identifican incendios independientes.")
        st.caption(f"Mapa: {len(mapped):,} celdas-día del intervalo seleccionado. Los indicadores superiores y el calendario usan todo el conjunto filtrado. El fondo cartográfico depende de conexión a internet.")
    else:
        st.info("Sin celdas activas en el intervalo.")
    day_df = daily_activity(cells)
    st.line_chart(day_df.set_index("date")[["active_cell_days", "raw_detections"]], x_label="Día UTC", y_label="Registros / celdas-día")

with t2:
    st.subheader("Calendario de actividad: año × mes")
    calendar_region = st.selectbox("Región del calendario", ["Sin recorte adicional", *REGIONS])
    calendar_data = observations.copy()
    if calendar_region in REGIONS:
        cw, cs, ce, cn = REGIONS[calendar_region]
        calendar_data = calendar_data.loc[calendar_data.longitude.between(cw, ce) & calendar_data.latitude.between(cs, cn)]
    years_available = sorted(observations.acquired_utc.dt.year.unique().tolist())
    selected_years = st.multiselect("Años del calendario", years_available, default=years_available)
    calendar_data = calendar_data.loc[calendar_data.acquired_utc.dt.year.isin(selected_years)]
    series = st.selectbox("Serie del calendario", ["Unión observada (celdas-día)", "MODIS observado (celdas-día)", "VIIRS observado (celdas-día)", "Reconciliada experimental (celdas-periodo)"])
    calendar_table = sensor_calendar(calendar_data, cell_m)
    columns = {"Unión observada (celdas-día)": "observed_union_cell_days", "MODIS observado (celdas-día)": "modis_cell_days", "VIIRS observado (celdas-día)": "viirs_cell_days"}
    chart_data = calendar_table
    value_column = columns.get(series, "reconciled_viirs")
    unit = "Celdas-día"
    if series.startswith("Reconciliada"):
        unit = "Celdas-periodo estimadas"
        if not historical_mode or sample_flag:
            chart_data = pd.DataFrame()
            st.info("Para esta serie carga el historial con productos verificados por metadatos en el modo Históricos MODIS C6.1 / S-NPP C2. Los datos sintéticos solo prueban la interfaz.")
        else:
            evaluation = diagnose_overlap(calendar_data, cell_m)
            chart_data = experimental_calendar(evaluation.normalization)
            st.dataframe(evaluation.normalization, use_container_width=True, hide_index=True)
            st.caption("Solo se muestra VIIRS reconciliado a escala MODIS en años reservados con soporte mínimo. El estimador es de celdas-periodo emparejadas: no se aplica a las celdas-día mensuales ni se suma a MODIS. IC 95% en la tabla: incertidumbre del factor, no de cobertura. Método experimental, no calibración validada.")
    if chart_data.empty or chart_data[value_column].dropna().empty:
        st.info("Sin información suficiente para la serie, región y años seleccionados. No equivale a cero actividad.")
    else:
        pivot = chart_data.pivot(index="year", columns="month", values=value_column).reindex(index=selected_years, columns=list(range(1, 13)))
        fig = go.Figure(data=go.Heatmap(z=pivot.values, x=MONTHS, y=[str(y) for y in pivot.index], zmin=0, zmax=float(chart_data[value_column].max()), colorscale="YlOrRd", colorbar={"title":unit}, hovertemplate="Año %{y}<br>Mes %{x}<br>Valor %{z:,.0f}<extra></extra>"))
        fig.update_layout(xaxis_title="Mes", yaxis_title="Año", yaxis={"type": "category"}, margin=dict(l=5,r=5,t=15,b=5), height=max(280, 65 * len(pivot)))
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Celdas vacías = no hay observaciones cargadas para ese mes; NO equivalen necesariamente a actividad cero. Los valores no corrigen cambios de sensores ni cobertura de adquisición.")
    st.dataframe(calendar_table, use_container_width=True, hide_index=True)
    st.caption("La unión observada es agregación espacial-temporal, no corrección de detectabilidad. Un sensor sin registros en un mes se muestra sin información; la cobertura válida sigue siendo desconocida.")
    st.download_button("Exportar calendario observado por sensor", calendar_table.to_csv(index=False).encode("utf-8"), "firesync_calendar_observed.csv", "text/csv")
    st.subheader("Comparación diaria observada MODIS–VIIRS")
    daily_comparison = daily_sensor_activity(calendar_data, cell_m)
    if daily_comparison.empty:
        st.info("Sin observaciones diarias en la selección; no se infiere actividad cero.")
    else:
        st.line_chart(daily_comparison.set_index("date")[["modis_detections", "viirs_detections"]].rename(columns={"modis_detections": "MODIS · detecciones", "viirs_detections": "VIIRS · detecciones"}), x_label="Día UTC", y_label="Detecciones observadas por sensor")
        st.line_chart(daily_comparison.set_index("date")[["modis_cell_days", "viirs_cell_days"]].rename(columns={"modis_cell_days": "MODIS · celdas-día", "viirs_cell_days": "VIIRS · celdas-día"}), x_label="Día UTC", y_label="Celdas-día observadas por sensor")
        st.dataframe(daily_comparison, use_container_width=True, hide_index=True)
        st.download_button("Exportar comparación diaria", daily_comparison.to_csv(index=False).encode("utf-8"), "firesync_daily_observed.csv", "text/csv")
        st.caption("La coincidencia en un día UTC no exige horarios próximos. Para concordancia con ±60 minutos usa Validación MODIS↔VIIRS. Detecciones y celdas-día no equivalen a incendios únicos.")
    if series.startswith("Reconciliada") and not chart_data.empty:
        st.download_button("Exportar calendario experimental reservado", chart_data.to_csv(index=False).encode("utf-8"), "firesync_calendar_experimental.csv", "text/csv")

with t3:
    st.subheader("Actividad relativa frente al mismo mes de años anteriores")
    monthly = monthly_activity(cells)
    anomalies = historical_anomalies(monthly)
    computable = anomalies.dropna(subset=["ratio"]).sort_values("ratio", ascending=False)
    if computable.empty:
        st.info("Se necesitan al menos 2 años anteriores con observaciones para el mismo mes. Puedes importar archivos históricos de NASA FIRMS.")
    else:
        computable = computable.copy()
        computable["periodo"] = computable["year"].astype(str) + "-" + computable["month"].astype(str).str.zfill(2)
        st.bar_chart(computable.set_index("periodo")["ratio"], y_label="Veces el promedio histórico previo")
        st.dataframe(computable[["periodo", "active_cell_days", "prior_mean", "n_prior", "ratio", "z_score"]].rename(columns={"active_cell_days":"celdas_dia", "prior_mean":"promedio_previo", "n_prior":"años_previos", "ratio":"razon", "z_score":"z"}), use_container_width=True, hide_index=True)
        st.warning("Las razones son exploratorias; sólo son interpretables si la región, la cobertura temporal, el procesamiento y el sesgo entre sensores resultan comparables. No son alertas operativas verificadas.")

with t4:
    st.subheader("Trazabilidad y exportación")
    st.write("**Paso 1.** Normalizar nombres de columnas, UTC y procedencia del sensor.")
    st.write("**Paso 2.** Aplicar filtros de confianza separados: MODIS usa 0–100; VIIRS usa l/n/h.")
    st.write(f"**Paso 3.** Proyectar a EPSG:6933 y agregar en celdas de {cell_m:,} m por día UTC.")
    st.write("**Paso 4.** Calcular el conteo de celdas-día y el calendario mensual, sin sumar FRP entre sensores.")
    st.write("**Paso 5.** Comparar períodos contra años anteriores disponibles (exploratorio, sin extrapolación predictiva).")
    st.warning("ALCANCE CIENTÍFICO: la ingestión y la concordancia se han comprobado con agosto de 2024. Faltan años independientes y control de sobrepasadas, ángulo, nubes y cobertura para validar una corrección de detectabilidad. No hay modelo predictivo de IA ni comparabilidad demostrada de toda la serie 2000–2026.")
    st.dataframe(observations.head(250), use_container_width=True, hide_index=True)
    if historical_mode:
        st.write("Manifiestos por archivo: colección/plataforma comprobadas por metadatos; autenticidad local no certificada.")
        with st.expander("Ver manifiestos y hashes de origen"):
            st.json(import_manifest)
        st.download_button("Exportar observaciones con procedencia", observations.to_csv(index=False).encode("utf-8"), "firesync_observations_traceable.csv", "text/csv")
    st.download_button("⬇️ Exportar celdas-día observadas (CSV)", cells.to_csv(index=False).encode("utf-8"), "firesync_cells_utc.csv", "text/csv")
    st.markdown("**Fuentes**: [NASA FIRMS](https://www.earthdata.nasa.gov/data/tools/firms) · [API de áreas](https://firms.modaps.eosdis.nasa.gov/api/area) · [Archivo histórico](https://firms.modaps.eosdis.nasa.gov/download/)")

with t5:
    st.subheader("Concordancia condicional y normalización experimental")
    if sample_flag:
        st.warning("DATOS SINTÉTICOS: esta demostración no aporta evidencia de calibración satelital.")
    st.write("Se comparan celdas comunes en adquisiciones emparejadas desde 2012. Ningún sensor es verdad de referencia. Los CSV de píxeles de calor no acreditan cobertura ni ausencia de actividad.")
    tolerance = st.slider("Tolerancia temporal (± minutos)", 1, 180, 60)
    use_bbox = st.checkbox("Recortar una AOI para esta validación", value=False)
    validation_bbox = None
    if use_bbox:
        aw = st.number_input("AOI oeste", -180., 180., -76.5)
        ass = st.number_input("AOI sur", -85., 85., -12.5)
        ae = st.number_input("AOI este", -180., 180., -72.)
        an = st.number_input("AOI norte", -85., 85., -7.)
        validation_bbox = (aw, ass, ae, an)
    st.caption("Sin recorte, todos los archivos cargados se consideran una misma AOI; comprueba que comparten región y productos. Se conservan los filtros de confianza de la barra lateral.")
    try:
        diagnostic = diagnose_overlap(observations, cell_m, tolerance, bbox=validation_bbox)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.caption(f"Registros excluidos (fecha, sensor, coordenadas o AOI): {diagnostic.excluded_records}. Adquisiciones sin pareja: {diagnostic.unpaired_acquisitions}.")
        if diagnostic.periods.empty:
            st.info("insuficiente información: no hay adquisiciones MODIS y VIIRS emparejables desde 2012 en esta AOI y tolerancia.")
        else:
            st.write("Diagnóstico por AOI, año y mes (unidades: celdas-periodo, no celdas-día ni incendios).")
            matched = int(diagnostic.periods.matched_cells.sum())
            union = int(diagnostic.periods.union_cells.sum())
            st.markdown(f"**{len(diagnostic.periods):,} parejas temporales** en **{diagnostic.periods.date.nunique()} días** · **{matched:,} coincidencias de celda-periodo** · **Jaccard condicional: {matched / union:.2%}**. Ningún sensor se interpreta como verdad de referencia.")
            st.dataframe(diagnostic.monthly, use_container_width=True, hide_index=True)
            st.caption("viirs_given_modis = coincidencias / MODIS; modis_given_viirs = coincidencias / VIIRS. Son análogos condicionales a recall/precisión, sin verdad de referencia. paired_days/paired_periods describen soporte observado, no días de cobertura válida.")
            st.write("Evaluación por mes: último año reservado, entrenamiento exclusivamente en años anteriores. Factor experimental VIIRS → escala MODIS; no se aplica a la fase 1 ni a años sin solapamiento.")
            st.dataframe(diagnostic.normalization, use_container_width=True, hide_index=True)
            st.caption("observed_* y reconciled_* corresponden solo al año reservado. IC 95% por bootstrap de años de entrenamiento (1000 réplicas, semilla 42); los conteos observados son exactos para el CSV. Su incertidumbre de cobertura/detección es desconocida. Los IC reconciliados solo propagan incertidumbre del factor; no son intervalos de incendios reales ni de predicción.")
            insufficient = diagnostic.normalization.loc[diagnostic.normalization.status == "insuficiente información"]
            if not insufficient.empty:
                st.info("insuficiente información para uno o más meses: consulta reason y el soporte de cada partición; no se calcula factor ni intervalo para esos meses.")
            st.download_button("Exportar diagnóstico mensual", diagnostic.monthly.to_csv(index=False).encode("utf-8"), "firesync_overlap_monthly.csv", "text/csv")
            st.download_button("Exportar normalización experimental", diagnostic.normalization.to_csv(index=False).encode("utf-8"), "firesync_normalization_experimental.csv", "text/csv")
            with st.expander("Auditar parejas temporales"):
                st.dataframe(diagnostic.periods, use_container_width=True, hide_index=True)
        st.warning("No es una calibración científicamente validada. Sesgos por nubes, cobertura, órbita, constelación, fronteras de celda y selección de detecciones persisten; un IC estrecho no los descarta.")

st.divider()
st.caption("Proyecto experimental para NASA Space Apps Challenge. No utilizar como único soporte para decisiones de emergencia.")
