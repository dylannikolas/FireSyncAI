# FireSync AI — resultados de fase 3

> Actualización posterior: el usuario aportó originales de agosto de 2024. Su procesamiento real se documenta en [REAL_DATA_VALIDATION.md](REAL_DATA_VALIDATION.md). Este informe conserva el estado de la entrega inicial, antes de recibirlos.

Fecha de ejecución: **2026-11-15**, zona local America/Lima; metadatos de importación en UTC. Implementación de integración histórica, calendario y evaluación preparada. **No se logró incorporar un subconjunto auténtico NASA por bloqueo de red de Python. No se afirma calibración validada.**

## Archivos modificados o añadidos

| Archivo | Resultado |
| --- | --- |
| `firesync/history.py` | Importación estricta por producto, metadatos originales, hashes, rechazo con motivos, selección SP/NRT y CLI reproducible con manifiesto/versiones/parámetros. |
| `firesync/calendar.py` | Calendario mensual por sensor/unión y vista experimental solo para estimaciones reservadas con soporte. Ausencia de información conserva valores vacíos. |
| `firesync/nasa.py` | Consulta histórica SP por fechas, bloques ≤5 días, límite de 31 días, auditoría sin credenciales, fallo sin resultados parciales; opción pública S-NPP añadida. |
| `firesync/calibration.py` | Conserva el método de fase 2; añade esquemas de tablas vacías para exportar resultados sin información como CSV legibles. |
| `app.py` | Entrada histórica por producto y archivos locales, API histórica, cohortes SP/NRT, calendario interactivo por región/años/sensor, procedencia y exportaciones. Conserva cinco tabs y los modos previos. |
| `pyproject.toml` | Paquete instalable editable y comando `firesync-import`; dependencias desde `requirements.txt`. |
| `scripts/setup_windows.ps1` | Asistente opcional de entorno; no elimina entornos existentes. |
| `scripts/recover_cached_wheels.py` | Recuperación opcional de wheels Python puros ya existentes en caché local, sin descargas ni reutilizar binarios cp311. |
| `tests/test_history.py`, `tests/test_nasa_history.py` | Ingestión, metadatos, fechas, versiones, plataforma, calendarios, duplicados, vacío, CLI y respuestas API simuladas. |
| `tests/test_app.py` | Se mantiene el test previo y se añaden dos integraciones: calendario sin años y carga histórica local con fixtures artificiales. |
| `README.md`, `data/HISTORICAL_IMPORT.md`, `SUBMISSION.md` | Fuentes, flujo manual, comandos, filtros, semántica de unidades, estado de demostración y límites. |
| `.gitignore` | Excluye entorno de fase 3, wheels, metadatos de instalación y directorios de datos/reportes locales. |
| `PHASE3_RESULTS.md` | Este informe. |

Se revisaron código, instrucciones de tarea, tests y documentación de las fases anteriores. No se encontraron instrucciones `AGENTS.md` aplicables. No hay metadatos Git disponibles en esta carpeta, por lo que no existe comparación contra un commit. Se conservaron `firesync/core.py`, los tests del núcleo y calibración, los datos de demostración y su generador. El cambio a `datetime.timedelta` en la ventana del mapa conserva sus 60 días y elimina el aviso anterior de compatibilidad NumPy/pandas.

## Fuentes verificadas y productos objetivo

Se consultaron durante esta ejecución las páginas oficiales:

- [Archivo FIRMS](https://firms.modaps.eosdis.nasa.gov/download/): acceso mediante autenticación y productos/periodos disponibles; S-NPP comienza el 20 de enero de 2012.
- [Readme oficial de descargas](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt): nombres de producto estándar MODIS `fire_archive_M-C61_*` (MCD14ML) y S-NPP `fire_archive_SV-C2_*` (VNP14IMGTML), diferenciados de NRT.
- [API de áreas](https://firms.modaps.eosdis.nasa.gov/api/area/): fecha inicial explícita, solicitudes de 1–5 días y fuentes `MODIS_SP` / `VIIRS_SNPP_SP`.

El objetivo es MODIS Terra/Aqua C6.1, resolución nominal 1000 m, y VIIRS Suomi NPP C2, nominal 375 m. NOAA-20/21 no se admiten como sustitutos de S-NPP en la importación histórica estricta. La AOI inicial `(-76.5,-12.5,-72,-7)` es una caja aproximada en Amazonía peruana; no representa límites oficiales ni la totalidad del bioma. Hay sub-AOIs aproximadas para explorar Ucayali y Madre de Dios.

Las referencias documentales no son observaciones satelitales descargadas. El acceso web de documentación funcionó, pero eso no habilitó solicitudes HTTPS desde el proceso Python.

## Datos realmente procesados

**Observaciones auténticas NASA descargadas: 0. Observaciones auténticas NASA evaluadas: 0.** No había archivos históricos oficiales locales; los únicos CSV iniciales eran los de demostración sintética. No se utilizaron ni buscaron credenciales del usuario.

Se intentó desde Python una solicitud a `https://firms.modaps.eosdis.nasa.gov/data/country/modis/2023/modis_2023_Peru.csv`. Falló al abrir el socket con **WinError 10013**, antes de obtener respuesta HTTP. La disponibilidad de esa ruta candidata no pudo verificarse. No se guardó una descarga fallida como CSV ni se reconstruyeron observaciones a partir de ejemplos/documentación. La ruta recomendada de importación es descargar los archivos originales mediante la interfaz oficial y cargarlos manualmente.

Para comprobar la CLI con archivos existentes se ejecutó, marcando explícitamente el origen artificial:

```powershell
.\.venv-phase3\Scripts\python.exe -m firesync.history --modis data/demo_modis.csv --viirs data/demo_viirs.csv --allow-nrt --processing NRT --synthetic --start 2022-01-01 --end 2026-11-15 --output data/processed/phase3_synthetic_smoke_v2
```

Resultado real de esta comprobación **sintética**:

| Entrada/salida | Resultado |
| --- | --- |
| `demo_modis.csv` | 291 filas artificiales; 289 aceptadas; 2 fuera de las fechas pedidas. Terra, versión `6.1NRT`. |
| `demo_viirs.csv` | 755 filas artificiales; todas rechazadas por plataforma N20, incompatible con S-NPP. Dos además fuera del periodo; los motivos se superponen. |
| Observaciones aceptadas | 289, todas etiquetadas `synthetic`, cohorte NRT. |
| Periodo observado aceptado | 2022-01-04 07:54 UTC a 2026-10-25 07:06 UTC. |
| Calendario observado | 57 filas año-mes con MODIS; VIIRS permanece sin información. |
| Parejas/evaluación | 0 parejas; no hay factor ni calendario experimental. Esto es insuficiencia de información, no actividad cero. |

Los siete archivos generados son `observations.csv`, `manifest.json`, `calendar.csv`, `overlap_pairs.csv`, `overlap_monthly.csv`, `evaluation.csv` y `calendar_experimental.csv`. Quedaron en el directorio local ignorado por Git. Los originales no cambiaron. Una primera comprobación previa también quedó en `data/processed/phase3_synthetic_smoke/`; la variante `_v2` contiene todas las salidas definitivas y versiones de software.

El test de interfaz histórica utiliza adicionalmente **120 registros artificiales** (60 por sensor) con metadatos compatibles, agosto de 2022/2023/2024, creados solo en un directorio temporal de pytest. Permite comprobar entrenamiento en 2022/2023, reserva de 2024 y la representación del factor conocido 1, pero no demuestra desempeño con NASA. La aplicación etiqueta archivos locales como procedencia no autenticada; no certifica sus metadatos como evidencia de autenticidad.

## Entorno y comandos realmente verificados

El `.venv` original sigue apuntando a un Python 3.11 no iniciable. No se borró ni modificó. Se creó **`.venv-phase3` con Python 3.12.1 y `--system-site-packages`** para usar las bibliotecas compatibles ya instaladas. Se recuperaron de caché wheels puros de pytest, pluggy, iniconfig y Plotly. El proyecto se instaló editable mediante `pyproject.toml`.

No se utilizó ninguna modificación de `sys.path`. Se verificaron los comandos equivalentes al procedimiento offline del README:

```powershell
python -m venv --system-site-packages .venv-phase3
python scripts/recover_cached_wheels.py
.\.venv-phase3\Scripts\python.exe -m pip install --no-index --find-links .offline-wheels -r requirements.txt
.\.venv-phase3\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv-phase3\Scripts\python.exe -m pip check
.\.venv-phase3\Scripts\python.exe -m pytest -q
```

`pip check`: **No broken requirements found**. No se alteraron paquetes globales. El entorno hereda bibliotecas de Python 3.12; no constituye prueba de instalación aislada limpia en otra máquina. El README incluye también los comandos normales de creación de un entorno limpio con conectividad. Recuperar caché solo es viable si existen los paquetes compatibles necesarios.

Versiones observadas: Python **3.12.1**, Streamlit **1.52.2**, pandas **2.2.3**, NumPy **2.5.4**, pyproj **3.7.1**, Plotly **6.9.0**, pydeck **0.9.1**, requests **2.32.3**, pytest **9.2.0**. Los manifiestos de CLI registran Python, versiones de las bibliotecas de procesamiento y parámetros del método.

La política local bloqueó la ejecución directa de `scripts/setup_windows.ps1`. No se cambió ni eludió la política: se ejecutaron los comandos Python/pip equivalentes directamente. El script PowerShell pasó el análisis sintáctico de `System.Management.Automation.Language.Parser`; su ejecución integral no pudo verificarse bajo esa política.

## Pruebas y aplicación

Comando final:

```powershell
.\.venv-phase3\Scripts\python.exe -m pytest -q
.\.venv-phase3\Scripts\python.exe -m compileall -q app.py firesync tests scripts
```

Resultado final: **61 passed in 12.93s**, código 0; `compileall`, código 0. Se conservan las 23 pruebas de fases previas y se añaden 38 casos. La suite no descarga datos ni requiere secretos. Todas las respuestas de pruebas API son mocks artificiales.

La cobertura funcional incluye:

- Plataforma/colección, resolución nominal, fecha/hora originales, hashes y alineación con filas de origen.
- Fechas imposibles, año bisiesto, límites inclusivos y comienzo de coincidencia en 2012-01-20.
- Horas inválidas, coordenadas/AOI, confianza separada por sensor, versión incorrecta y rechazo de NOAA-20 como S-NPP.
- Duplicados dentro/entre archivos; SP y NRT distintos incluso en la misma posición/fecha; archivos vacíos con cabecera frente a contenido ilegible.
- Agregación mensual por sensor y celdas-día, periodos sin información, estimación reservada solo con soporte y CSV vacíos legibles.
- CLI que conserva procedencia sintética y rechaza sobrescritura; particiones anuales/bootstrap cubiertos por fase 2.
- División API en ventanas inclusivas no superpuestas, rechazo antes de consultar de parámetros inválidos, errores sin clave y sin publicar resultados parciales.
- AppTest: métricas básicas conservadas al recortar validación, calendario sin años, archivos locales, y vista experimental claramente diferenciada.

Streamlit se inició con:

```powershell
.\.venv-phase3\Scripts\python.exe -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8513 --browser.gatherUsageStats false
```

La comprobación de `http://127.0.0.1:8513/_stcore/health` respondió **200, `ok`**. La representación e interacciones se comprobaron con AppTest, no mediante inspección visual manual del navegador. El origen predeterminado sigue siendo la demostración sintética, visiblemente rotulada. Streamlit conserva avisos de deprecación de `use_container_width` y de contexto del arnés AppTest; no son validación científica ni fallos de datos.

## Evaluación real pendiente y límites

No se publican Jaccard, MAE, factores ni intervalos supuestamente reales porque no se procesó ningún archivo auténtico. El procedimiento ya produce esas tablas cuando se aporten registros compatibles, separando por AOI/mes, reservando el último año y ajustando en al menos dos anteriores. Conserva umbrales de 20 días de entrenamiento, 10 reservados y 20 coincidencias por partición, bootstrap de años de entrenamiento (1000 réplicas, semilla 42). Estos umbrales no prueban suficiencia científica.

La unidad del estimador es **celda-periodo emparejada**, distinta de la **celda-día** del calendario observado. La vista experimental solo muestra el año reservado con soporte, sin multiplicar celdas-día completas por un factor de otra unidad, ni sumarlo a MODIS, ni extrapolar a años sin solapamiento. La unión observada es agregación, no una serie corregida por detectabilidad.

Persisten cobertura desconocida, nubes, diferencias orbitales, duración de pasadas, tamaño/origen de celda, sesgo de selección por detección y falta de referencia independiente. Un mes o sensor sin filas nunca implica ausencia de incendios. La confianza MODIS y VIIRS permanece separada; no se calibró FRP. No se cuentan incendios confirmados.

Para cerrar la demostración con datos reales: descargar un primer par oficial de un mes/AOI, conservar recibos y originales, importar con manifiesto, comprobar el calendario por sensor y después agregar años independientes suficientes para evaluación. Se necesitan datos de cobertura y validación externa antes de afirmar una calibración científica o comparabilidad de toda la serie histórica. Importación de archivos muy grandes/streaming, límites regionales oficiales y una instalación limpia con conectividad quedan sin verificar en esta ejecución.
