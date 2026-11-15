# FireSync AI

**Actividad térmica MODIS–VIIRS, comparable en espacio y tiempo, con trazabilidad explícita.**

Prototipo para NASA Space Apps Challenge 2026. Integra CSV de NASA FIRMS, preserva el sensor y sus metadatos, y permite explorar mapas, calendarios y concordancia entre detecciones. **No contiene un modelo predictivo de IA ni una calibración científica validada.** «AI» forma parte del nombre del proyecto, no describe una capacidad predictiva demostrada.

## Demostración web · GitHub Pages

Enlace previsto: **[https://dylannikolas.github.io/FireSyncAI/](https://dylannikolas.github.io/FireSyncAI/)**. Estará disponible después de subir los cambios y habilitar GitHub Pages desde la raíz de la rama `main`; todavía no se ha publicado como parte de esta preparación.

La página estática [index.html](index.html) reproduce directamente [el video MP4](videos/FireSyncAI_demo_30s.mp4) con controles HTML5 y presenta los indicadores observados y sus límites científicos. Se adapta a pantallas móviles. GitHub Pages aloja esta demostración; para usar el dashboard interactivo de Streamlit, sigue las instrucciones de ejecución local de abajo.

## Demostración comprobada

Amazonía peruana aproximada, **1–31 de agosto de 2024**, AOI W,S,E,N `-76.5,-12.5,-72,-7`.

| Indicador observado | Resultado |
| --- | ---: |
| Registros MODIS Terra/Aqua | 2,931 |
| Registros VIIRS Suomi NPP | 13,905 |
| Total de detecciones | **16,836** |
| Unión observada en cuadrícula de 1 km | **12,735 celdas-día** |
| Celdas-día registradas por ambos sensores | 650 |
| Parejas temporales a ±60 minutos | 41, en 21 días |
| Jaccard condicional de celdas-periodo | 0.8538% |

Estas unidades **no son incendios únicos**. Los originales fueron aportados por el usuario como descargas FIRMS; se verificaron metadatos y hashes, sin autenticar externamente una firma de NASA. Un mes permite diagnóstico de concordancia, no ajuste y evaluación por años independientes. Informe completo: [REAL_DATA_VALIDATION.md](REAL_DATA_VALIDATION.md).

## Inicio rápido en Windows

La copia pública incluye `data/demo_modis.csv` y `data/demo_viirs.csv`: **datos sintéticos de demostración**, sin evidencia satelital real. No requiere claves API. Después de instalar las dependencias, ejecuta:

```powershell
.\.venv-phase3\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8513
```

Abre **http://127.0.0.1:8513/** y conserva «Demostración simulada» para probar la copia pública. Elige Mapa, Calendario, Anomalías, Datos y metodología y Validación MODIS↔VIIRS. La vista `?source=real` requiere los originales locales y el directorio procesado descritos abajo; si faltan o cambian los hashes muestra un error, sin sustituirlos por datos sintéticos.

Para una instalación nueva con Python **3.11 o 3.12** funcional y conexión:

```powershell
python --version
python -m venv .venv-phase3
.\.venv-phase3\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-phase3\Scripts\python.exe -m pip install -e .
.\.venv-phase3\Scripts\python.exe -m pytest -q
.\.venv-phase3\Scripts\python.exe -m streamlit run app.py --server.port 8513
```

No hace falta activar PowerShell ni modificar `sys.path`. Si un entorno existente está roto, usa otro nombre, sin copiar extensiones de otra versión de Python. En esta máquina el antiguo `.venv` no funciona; se conservó y se comprobó `.venv-phase3` con Python 3.12.1, bibliotecas compatibles globales y wheels locales. Esa alternativa con `--system-site-packages` **no equivale a una instalación limpia**. Procedimiento offline y detalles: [METHODOLOGY.md](METHODOLOGY.md), [PHASE3_RESULTS.md](PHASE3_RESULTS.md).

## Datos NASA e importación reproducible

Fuentes: [NASA FIRMS Archive Download](https://firms.modaps.eosdis.nasa.gov/download/), [Readme oficial](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) y [API de áreas](https://firms.modaps.eosdis.nasa.gov/api/area/).

| Archivo original local | Producto declarado | Plataforma | Resolución nominal | Versión preservada |
| --- | --- | --- | --- | --- |
| `data/raw/fire_archive_M-C61_851101.csv` | MODIS C6.1, SP | Terra/Aqua | 1000 m | `61.03` |
| `data/raw/fire_archive_SV-C2_851102.csv` | VIIRS C2, SP | Suomi NPP | 375 m | `2` |

Son CSV mundiales de 773,697 y 3,582,707 filas, respectivamente. El importador lee por bloques de 100,000 filas, aplica AOI y fechas inclusivas y registra motivos de exclusión. Los originales permanecen intactos. Conserva el recibo de descarga fuera del repositorio. Los hashes completos y periodos efectivos están en el informe real.

Para construir la vista preparada en una copia nueva:

```powershell
.\.venv-phase3\Scripts\python.exe -m firesync.history --modis data/raw/fire_archive_M-C61_851101.csv --viirs data/raw/fire_archive_SV-C2_851102.csv --start 2024-08-01 --end 2024-08-31 --bbox -76.5 -12.5 -72 -7 --sensitivity --output data/processed/real_2024_08
```

La salida debe ser un directorio **nuevo**: no se sobrescriben resultados. Para repetir la validación en esta máquina usa, por ejemplo, `--output data/processed/real_2024_08_repro02`. La vista preparada siempre consulta `data/processed/real_2024_08/`. También puedes seleccionar **Históricos MODIS C6.1 / S-NPP C2** para importar originales desde la raíz de `data/raw/`, sus subcarpetas `modis/` y `viirs_snpp/`, o los controles de subida. El VIIRS mundial supera el límite habitual de subida: usa archivos locales.

Salidas: observaciones con procedencia, manifiesto con hashes y versiones, calendario mensual, comparación diaria, parejas temporales, diagnóstico mensual, evaluación, calendario experimental y sensibilidad de celda/tolerancia. Los conteos originales no se fuerzan a un valor esperado.

La API histórica permite subconjuntos SP de hasta 31 días en bloques de hasta 5. Necesita MAP_KEY y disponibilidad FIRMS. La demostración local **no depende de API ni credenciales**. Una caída de red no impide cargar los CSV guardados; el fondo cartográfico sí requiere acceso a teselas externas.

## Qué muestra el dashboard

1. **Mapa de actividad:** celdas-día por sensor, colores y rango de fechas. La vista real empieza con 25–31 de agosto para evitar saturación; indicadores y calendario mantienen el mes completo. Límite visual de 10,000 celdas con advertencia.
2. **Calendario histórico:** años/meses, región, MODIS, VIIRS y unión observada; gráficos diarios y descargas. Meses y sensores sin registros permanecen sin información. La vista reconciliada es experimental y exige soporte.
3. **Anomalías exploratorias:** comparación con el mismo mes de años anteriores, solo con historia suficiente. Agosto de 2024 aislado muestra que faltan años; no genera una alerta.
4. **Datos y metodología:** observaciones originales normalizadas, filtros, manifiestos, hashes y exportación.
5. **Validación MODIS↔VIIRS:** parejas cercanas en tiempo, coincidencias de celda y fracciones condicionales. Muestra insuficiencia de información para calibración cuando corresponde.

**Estados visibles:** observaciones reales aportadas por usuario; estimaciones experimentales solo con soporte; demostración sintética rotulada y separada. Los `demo_*.csv` son artificiales y no aportan evidencia satelital.

## Arquitectura

```text
CSV FIRMS local / API opcional
  → history.py: esquema, producto, AOI, fechas, hashes y auditoría
  → core.py: UTC, confianza por sensor, cuadrícula EPSG:6933
  → calendar.py: celdas-día mensuales y comparación diaria
  → calibration.py: parejas temporales y evaluación separada por años
  → app.py: cinco pestañas, filtros, leyendas y exportaciones

validated_data.py verifica la vista real preparada contra los hashes originales.
```

Python, pandas, NumPy y pyproj procesan los datos; Streamlit, PyDeck y Plotly presentan la aplicación. `tests/` cubre casos artificiales identificados y dos integraciones opcionales con los datos reales locales. `scripts/` contiene instalación, auditoría y empaquetado. El paquete instalable ofrece `firesync-import`.

## Metodología y límites científicos

- Cuadrícula común de igual área EPSG:6933; `floor(x/cell_m)` y `floor(y/cell_m)`. Una celda-día es actividad observada en una celda durante un día UTC, no un incidente.
- La unión observada reduce repetición espacial-temporal; **no corrige detectabilidad**. Resolución nominal no es tamaño exacto de huella.
- Concordancia: emparejamiento cronológico uno a uno con el timestamp VIIRS más cercano, ±60 minutos por defecto, sin reutilizar timestamps ni cruzar años. Se comparan conjuntos de celdas-periodo; 205 timestamps de este mes quedaron sin pareja.
- Ningún sensor es verdad de referencia. Las fracciones condicionales y Jaccard no son exactitud ni sensibilidad real. Celdas-periodo y celdas-día son unidades diferentes.
- La normalización experimental mensual reserva el último año y usa anteriores para ajustar. Exige al menos dos años de entrenamiento, otro reservado, soporte de días y coincidencias; incluye bootstrap de años. **Con agosto de 2024 no se calcula factor ni intervalo.**
- Nubosidad, cobertura válida, ángulo, horario, constelación y selección por detección no están controlados. Ausencia de filas no demuestra ausencia de incendios. MODIS no tiene registros en esta AOI los días 7 y 26; se muestran huecos.
- Confianza MODIS 0–100 y VIIRS l/n/h siguen separadas. No se calibró FRP ni se filtró silenciosamente `type`. No todo píxel de calor es fuego de vegetación.
- No hay predicción, alerta operacional ni calibración validada de la serie completa 2000–2026.

Detalles del estimador, umbrales e intervalos: [METHODOLOGY.md](METHODOLOGY.md). Evidencia real y sensibilidad: [REAL_DATA_VALIDATION.md](REAL_DATA_VALIDATION.md).

## Verificación, entrega y seguridad

```powershell
.\.venv-phase3\Scripts\python.exe -m pytest -q
.\.venv-phase3\Scripts\python.exe -m pip check
.\.venv-phase3\Scripts\python.exe scripts/submission_audit.py
.\.venv-phase3\Scripts\python.exe scripts/build_submission.py
```

El ZIP de código se genera en `dist/FireSyncAI_submission.zip`; incluye demostración sintética rotulada y documentación, **no** CSV mundiales, resultados observados, entornos ni credenciales. Para demostrar los datos reales en otro equipo hay que facilitar los originales e importar la AOI por separado.

`.gitignore` excluye `data/raw/`, `data/processed/`, archivos `fire_archive_*.csv` y `DL_FIRE_*.zip` incluso fuera de esas carpetas, entornos, `.env`, secretos de Streamlit y claves privadas. `.env.example` solo contiene un campo vacío. La auditoría prueba las reglas con Git y busca patrones de secretos sin imprimir valores. Es heurística, no una certificación. El repositorio local se prepara sin publicar; revisa [GITHUB_PREPUBLICATION.md](GITHUB_PREPUBLICATION.md) y el inventario antes del primer commit o push. Nunca uses `git add -f` para archivos excluidos.

## Material para presentar

- [Ver o descargar el video de demostración MP4](videos/FireSyncAI_demo_30s.mp4). El video público está incluido en `videos/`. Script: `scripts/generate_demo_video.py`; dependencias opcionales en `requirements-video.txt`.
- [Descripción bilingüe del proyecto](SUBMISSION.md): problema, solución, innovación, impacto y resultados demostrados.
- [Guion alternativo de 90 segundos](DEMO_VIDEO_90S.md): borrador previo; el MP4 final solicitado dura 29 segundos.
- [Lista final de entrega](FINAL_SUBMISSION_CHECKLIST.md): pruebas, revisión visual, exclusiones y pasos humanos pendientes.
- [Validación real](REAL_DATA_VALIDATION.md), [fase 2](PHASE2_RESULTS.md) y [entrega inicial de fase 3](PHASE3_RESULTS.md): evidencia y evolución del prototipo.
