# 🔥 FireSync AI — NASA Space Apps 2026

> Archivo técnico preservado al preparar la entrega. Para instalación y estado actual usa [README.md](README.md); para la revisión de presentación usa [FINAL_SUBMISSION_CHECKLIST.md](FINAL_SUBMISSION_CHECKLIST.md). Los comandos y conteos de pruebas de las fases anteriores se conservan como contexto histórico.

**Prototipo web de armonización espacial-temporal de puntos críticos MODIS y VIIRS.**

> **Estado científico**: **MVP de exploración** con diagnóstico de concordancia y normalización experimental condicional MODIS–VIIRS. La calibración de detectabilidad y la cobertura satelital **no están validadas**; los conteos no equivalen al número de incendios reales. Los datos de demostración son **SINTÉTICOS** y no se deben presentar como observaciones de NASA.

## Instalación (Windows PowerShell)

Se necesita **Python 3.11 o 3.12** y conexión a internet para instalar dependencias:

```powershell
cd FireSyncAI
python --version
python -m venv .venv-phase3
.\.venv-phase3\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-phase3\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv-phase3\Scripts\python.exe -m pytest -q
.\.venv-phase3\Scripts\python.exe -m streamlit run app.py
```

`python` debe apuntar a una instalación funcional de Python 3.11 o 3.12. No hace falta activar el entorno ni cambiar `sys.path`. Si ya existe un entorno roto, utiliza un nombre nuevo; no borres ni reutilices sus extensiones de otra versión de Python. En esta máquina `.venv` apunta a un Python 3.11 no disponible: se conservó y se preparó `.venv-phase3` con Python 3.12.1.

El asistente opcional `scripts/setup_windows.ps1` implementa estos pasos. Si la política de PowerShell impide ejecutar scripts, usa directamente los comandos anteriores, sin cambiar la política. Para un entorno sin red que **ya tiene** las dependencias científicas compatibles instaladas, se verificó este procedimiento alternativo:

```powershell
python scripts/recover_cached_wheels.py
python -m venv --system-site-packages .venv-phase3
.\.venv-phase3\Scripts\python.exe -m pip install --no-index --find-links .offline-wheels -r requirements.txt
.\.venv-phase3\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv-phase3\Scripts\python.exe -m pip check
.\.venv-phase3\Scripts\python.exe -m pytest -q
```

Este segundo método usa paquetes globales y wheels Python puros ya presentes en caché; **no es una instalación aislada limpia** ni garantiza que otra máquina tenga esas dependencias. Si la caché no está disponible, necesitas conexión o un wheelhouse completo para tu versión de Python. El código no busca paquetes en `.venv` ni altera manualmente `sys.path`.

Abre `http://localhost:8501`.

## Uso

1. **Demostración simulada**: funciona sin credenciales. Son registros artificiales de Ucayali/selva peruana, 2022–2026, solo para probar la interfaz.
2. **Cargar CSV históricos**: [archivo NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/download/), selecciona región común, productos MODIS C6.1 y VIIRS, exportación CSV. Se aceptan varios archivos a la vez. Para analizar un largo historial hay que descargarlos por años y mantener la misma región.
3. **NASA FIRMS · CSV público 24h**: descarga archivos globales publicados por NASA sin MAP_KEY, recortándolos a una caja geográfica editable; requiere acceso HTTPS a FIRMS y que el servicio tenga disponibles los CSV. Si falla, usa el origen con API o CSV manual.
4. **NASA FIRMS · recientes**: obtén MAP_KEY gratuita en https://firms.modaps.eosdis.nasa.gov/api/map_key; introduce la clave **únicamente** en el campo privado de Streamlit. Por defecto el ejemplo de límites geográficos corresponde a una caja aproximada de Amazonía peruana, no una división administrativa oficial. Consulta de 1–5 días por fuente.
5. Explora el mapa, calendario, anomalías y exporta las celdas-día a CSV.
6. **Históricos MODIS C6.1 / S-NPP C2**: carga CSV por producto o selecciona archivos locales en `data/raw/modis/` y `data/raw/viirs_snpp/`; valida colección, satélite, fechas y calidad de cada fila, conserva procedencia y permite elegir SP o NRT sin mezclarlos.
7. **NASA FIRMS · histórico API**: consulta un subconjunto SP de hasta 31 días con MAP_KEY privada y fechas explícitas. Cada solicitud cubre como máximo 5 días; disponibilidad histórica y cuota dependen de FIRMS. Para una primera consulta usa un mes de un año cerrado, por ejemplo agosto de 2023, y la misma AOI para ambos sensores.

## Datos y metodología

- Campos aceptados: `latitude, longitude, acq_date, acq_time` y `instrument` (si falta, el sistema deduce a partir del satélite o nombre del archivo); campos auxiliares: `confidence`, `frp`, `version`, `satellite`.
- Tiempo en **UTC**; `acq_time` NASA en formato HHMM con ceros a la izquierda.
- Proyección **EPSG:6933 de igual área**: agregación en cuadrículas (1000 m por lado por defecto) y día UTC. Esto **reduce el doble conteo de registros en una misma celda-día**. La unidad resultante se denomina **celda-día activa observada**: no es fuego individual, área quemada ni un incendio confirmado.
- MODIS tiene píxel nominal 1 km, VIIRS 375 m; confianza MODIS 0–100 y VIIRS l/n/h. No son valores equivalentes.
- Se conserva el origen por sensor; no se suman ni equiparan FRP de sensores distintos.
- Calendario mensual: suma observada de celdas-día. Un mes no presente **no significa 0 incendios**.
- Anomalías: razón vs media del mismo mes en años **anteriores**; se requieren al menos 2 años históricos comparables. No es predicción ni alarma operacional. No ajustar solo por tener más observaciones NASA: los cambios de sensor, nubosidad, órbita, horas de sobrepasada y datos faltantes son confusores.

### Limitaciones que deben resolverse antes de presentar una verdadera serie armonizada 2000–2026

1. Calibración de **sensibilidad** MODIS↔VIIRS en años simultáneos, con evaluación por año y región de prueba, no solo mezcla de registros.
2. Control explícito por **cobertura**: pasadas satelitales válidas, nubosidad, datos ausentes, horario y cambios de constelación, no inferir ceros desde CSV de focos.
3. Sensibilidad al tamaño de celda y cambios en el límite de celda; comparación independiente con datos de referencia cuando existan.
4. Separar detecciones de calor persistente industrial/volcánico de vegetación cuando exista `type` validado.
5. Validación cuantitativa: coincidencia entre sensores en solapamiento 2012+, sesgos mensuales, estabilidad temporal y errores de evaluación fuera de muestra.

## Fase 3: historial auténtico y calendario por sensor

**Actualización con datos reales aportados por el usuario:** se procesaron los originales mundiales de agosto de 2024 y se verificaron **2,931 registros MODIS y 13,905 VIIRS S-NPP** en la AOI, sin modificar los CSV. Selecciona **Observaciones FIRMS · agosto 2024 (AOI)** o abre `http://127.0.0.1:8513/?source=real`. Resultados, hashes, concordancia, límites y comandos en [REAL_DATA_VALIDATION.md](REAL_DATA_VALIDATION.md). El estado previo sin originales locales queda documentado en [PHASE3_RESULTS.md](PHASE3_RESULTS.md). Un solo mes no permite calibración por años.

### Descargar un primer subconjunto oficial

En [NASA FIRMS Archive Download](https://firms.modaps.eosdis.nasa.gov/download/) autentícate con Earthdata o el método indicado por FIRMS. Pide CSV del mismo periodo y área para ambos productos; conserva el recibo y los archivos originales, sin reescribirlos. La [guía de archivos FIRMS](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) distingue:

| Producto de estudio | Archivo estándar | Colección | Plataforma | Resolución nominal |
| --- | --- | --- | --- | --- |
| MODIS Active Fire / MCD14ML | `fire_archive_M-C61_*` | 6.1 | Terra y Aqua | 1000 m |
| VIIRS Active Fire / VNP14IMGTML | `fire_archive_SV-C2_*` | 2 | Suomi NPP | 375 m |

La resolución es nominal del producto, no el tamaño exacto de cada huella; se preservan `scan`/`track` cuando existen. Se retienen satélite, instrumento, versión y fechas originales. NOAA-20/21 no sustituyen S-NPP en este importador. Los modos genéricos de fase 1 siguen disponibles para explorar otras fuentes, con advertencias de comparabilidad.

El [archivo oficial](https://firms.modaps.eosdis.nasa.gov/download/) sitúa el inicio del registro VIIRS S-NPP en **2012-01-20**: este es el inicio mínimo del importador de coincidencia, no una declaración de cobertura completa desde ese día. Enero de 2012 es parcial. NRT y SP tienen distinta disponibilidad y latencia; verifica las fechas efectivas del producto en FIRMS antes de solicitarlo.

Para una primera demostración pequeña pide **2023-08-01 a 2023-08-31**, caja aproximada W,S,E,N **`-76.5,-12.5,-72,-7`**. Es una AOI de estudio en Amazonía peruana, **no** la delimitación completa de Perú o de su bioma amazónico. Para una evaluación temporal posterior descarga, por ejemplo, agosto de **2022, 2023 y 2024**, manteniendo productos, región y filtros; no se presupone que esos archivos alcancen soporte suficiente.

Guarda los archivos oficiales en:

```text
data/raw/modis/fire_archive_M-C61_....csv
data/raw/viirs_snpp/fire_archive_SV-C2_....csv
```

También se reconocen directamente en `data/raw/` los nombres `fire_archive_M-C61_*.csv` y `fire_archive_SV-C2_*.csv`, sin mover originales. Los archivos locales se importan por bloques con caché y auditoría mundial. Para el VIIRS mundial de 291 MB usa la vía local: puede superar el límite de subida del servidor.

Se excluyen de Git `data/raw/`, `data/processed/`, entornos y reportes locales. Los CSV pueden subirse directamente a la app sin copiarlos al proyecto. No copies los `demo_*.csv` como si fueran originales NASA.

### Importación reproducible y auditoría

Ejemplo PowerShell con archivos que debes descargar; las rutas no representan datos incluidos en el repositorio:

```powershell
$modisFiles = (Get-ChildItem -LiteralPath data/raw/modis -Filter '*.csv').FullName
$viirsFiles = (Get-ChildItem -LiteralPath data/raw/viirs_snpp -Filter '*.csv').FullName
.\.venv-phase3\Scripts\python.exe -m firesync.history --modis $modisFiles --viirs $viirsFiles --start 2022-08-01 --end 2024-08-31 --bbox -76.5 -12.5 -72 -7 --output data/processed/amazon_2022_2024_run01
```

`--output` debe ser un directorio nuevo: no se sobrescriben resultados existentes. También queda instalado el comando `firesync-import` dentro del entorno. Las salidas son:

- `observations.csv`: registros aceptados, con `acquired_utc`, sensor, satélite, colección, resolución nominal, procesamiento, fecha/hora originales, archivo, SHA-256 y número de fila original.
- `manifest.json`: hashes de entrada, versiones efectivas, fechas pedidas y observadas, AOI, aceptados/excluidos, motivos (pueden superponerse), duplicados, filtros, versiones de software y parámetros del bootstrap/evaluación.
- `calendar.csv`: celdas-día por MODIS, VIIRS y unión observada; sensor/mes ausente queda vacío, no cero.
- `overlap_pairs.csv`, `overlap_monthly.csv`: parejas temporales y diagnóstico de concordancia.
- `evaluation.csv`, `calendar_experimental.csv`: ajuste solo en años anteriores y evaluación del último año de cada mes. Sin soporte, no hay factor y el calendario experimental queda vacío con cabecera.

La importación por defecto exige SP y acepta versiones MODIS `6.1/6.10/61/61.03`, VIIRS `2/2.0/2.00`, satélite correspondiente y confianza válida de cada sensor. `61.03` e `instrument=SNPP` se añadieron explícitamente al revisar los archivos aportados; se conservan los identificadores originales. No es una equivalencia de confianza. Faltas de esquema generan error; coordenadas/fechas/horas inválidas, productos incompatibles y registros fuera del periodo/AOI se excluyen con motivos. Fechas estrictas YYYY-MM-DD y HHMM UTC; límites inicial/final inclusivos. Los filtros adicionales se declaran con `--modis-min` y `--exclude-viirs-low` y se registran en el manifiesto. No se filtra `type` silenciosamente ni se usa FRP para calibrar.

Para admitir NRT usa `--allow-nrt` y selecciona la cohorte `--processing NRT`; el análisis predeterminado sigue siendo SP. La app ofrece la misma separación. No se reemplazan ni fusionan silenciosamente versiones distintas. Los CSV originales permanecen intactos. Un archivo local se etiqueta `user_supplied_unverified`: la consistencia de metadatos y el hash no certifican origen NASA. Los fixtures deben usar `--synthetic` y nunca aportan evidencia observacional.

### API por fechas y seguridad

La [API oficial de áreas](https://firms.modaps.eosdis.nasa.gov/api/area/) admite fecha inicial, bloques de 1–5 días y las fuentes `MODIS_SP` / `VIIRS_SNPP_SP`. FireSync limita cada acción histórica a 31 días para priorizar un subconjunto pequeño. Introduce la MAP_KEY en el campo privado o en `FIRMS_MAP_KEY` del entorno; no la pases en archivos del proyecto, manifiestos o argumentos de CLI. No se guarda en las URL de procedencia ni se muestra en errores.

La app conserva la identidad del producto consultado y un registro por bloque con fecha, días, filas y hash del texto recibido, sin clave. El hash principal de esta vía corresponde al CSV serializado desde la respuesta parseada; se declara ese alcance. Si falla cualquier bloque/producto se muestra el error y no se publica una descarga parcial como exitosa. Respuesta ilegible o sin esquema es error; cabecera válida sin filas es «sin información», sin interpretar ausencia de incendios.

### Calendario y evaluación

El tab de calendario conserva la unión observada de fase 1 y añade selector MODIS/VIIRS, región aproximada y años. **Unión observada no es calibración**. Cada sensor conserva su conteo de celdas-día y los huecos se mantienen vacíos.

La vista **Reconciliada experimental** requiere el modo histórico con producto/cohorte identificados y soporte de fase 2. Solo grafica VIIRS reexpresado en escala MODIS para el año reservado, en **celdas-periodo emparejadas**. No transforma celdas-día completas con un factor entrenado sobre otra unidad, no suma la estimación a MODIS ni rellena años sin validación. La tabla incluye intervalo del factor propagado, soporte y MAE antes/después; esos intervalos no incorporan incertidumbre de cobertura. Cambiar región o años recalcula las particiones; documenta tu selección y no la elijas buscando el menor error.

**Pendiente:** ampliar agosto de 2024 con varios años reales independientes para ajuste y evaluación, conservar recibos de descarga y controlar cobertura. Ya se publican métricas de concordancia observada en [REAL_DATA_VALIDATION.md](REAL_DATA_VALIDATION.md), pero no se afirma calibración validada. Nubes, horarios, huellas válidas y referencia independiente siguen siendo limitaciones descritas en fase 2.

## Fase 2: validación MODIS↔VIIRS exploratoria

El nuevo tab **Validación MODIS↔VIIRS** conserva las visualizaciones de fase 1 y sus conteos originales. Permite recortar una AOI por caja geográfica y cambiar la tolerancia temporal. Sin recorte, el conjunto cargado representa una sola AOI: el analista debe comprobar que los archivos comparten región y productos. La API Python `firesync.calibration.diagnose_overlap` admite además `aoi_column` para analizar varias zonas independientemente. No se hacen consultas externas desde el módulo.

### Comparación y soporte observado

1. Solo se usan registros válidos MODIS/VIIRS desde 2012 en EPSG:6933, con la misma cuadrícula y origen fijo que fase 1 (`floor(x/cell_m)`, `floor(y/cell_m)`). Los filtros de confianza siguen separados por sensor; la calibración no utiliza FRP.
2. Cada timestamp UTC con detecciones de MODIS se empareja, en orden cronológico, con el timestamp VIIRS disponible más cercano dentro de **±60 minutos** por defecto (empates: el anterior). Cada timestamp se usa una vez. No se encadenan ventanas ni se comparan todas las detecciones de un mismo día. Se permite cruzar medianoche/mes, asignando el periodo a la fecha MODIS; **se prohíbe cruzar años** para evitar contaminación de las particiones. Es un algoritmo voraz determinista, no un emparejamiento global óptimo.
3. Para cada pareja se comparan conjuntos de celdas. Las repeticiones dentro de celda/sensor/timestamp cuentan una sola vez. La unidad mensual es **celda-periodo observada**; una celda en dos parejas cuenta dos veces. No debe confundirse con la celda-día de fase 1.
4. Por AOI, año y mes se publican conteos de cada sensor, coincidencias, exclusivos, Jaccard y `viirs_given_modis = coincidencias/MODIS`, `modis_given_viirs = coincidencias/VIIRS`. Estas dos fracciones son análogos condicionales de recall/precisión intercambiando sensor de referencia; **ninguno representa verdad**, sensibilidad real ni exactitud. Se muestran días y periodos emparejados, registros excluidos y adquisiciones sin pareja; la tabla de parejas permite auditar tiempos y desfases.

**Cobertura válida desconocida:** un timestamp con píxeles de calor es solo un proxy de adquisición. No demuestra que ambos sensores observaron toda la AOI, ni prueba cielo despejado o ausencia de actividad en celdas sin detección. Por eso `paired_days` no se llama días de cobertura válida. Los días/meses sin parejas se omiten, nunca se rellenan con ceros. No se dispone de denominador de celdas negativas válidas; no se calculan especificidad ni falsos positivos reales. El análisis está condicionado a que ambos sensores registren alguna detección próxima en la AOI.

### Normalización experimental y evaluación por años

Se calcula un factor **por AOI y mes del calendario**, no un cociente global de puntos. El último año con parejas de ese mes se reserva completo para evaluación; todos los anteriores son entrenamiento. Sobre los conteos diarios de celdas-periodo de entrenamiento se ajusta:

`factor VIIRS→MODIS = exp(media(log(MODIS_día / VIIRS_día)))`

Solo se calcula con al menos **2 años de entrenamiento y 1 posterior reservado**, **20 días emparejados de entrenamiento**, **10 días reservados** y **20 coincidencias en cada partición**. Son umbrales prácticos de soporte, no criterios probados de suficiencia científica. Ambos conteos diarios son positivos por construcción de las parejas. Si falta soporte se devuelve **«insuficiente información»**, con motivos y factores/intervalos ausentes; tampoco se extrapola a meses sin parejas o a 2000–2011.

La tabla muestra años y soporte de cada partición, rango de factores anuales de entrenamiento (variabilidad interanual), conteos observados de ambos sensores en el año reservado, VIIRS reexpresado en la escala condicional MODIS y MAE diario reservado antes/después del ajuste. El factor y su IC no usan los conteos del año reservado; el soporte de ese año solo determina si se puede publicar una evaluación. El último año cargado puede ser parcial y no es automáticamente representativo.

El **IC percentil 95%** se obtiene mediante **1000 réplicas bootstrap de bloques de años de entrenamiento**, con reemplazo, semilla 42; cada bloque conserva todos sus días. Se recalcula el mismo estimador en cada réplica y se propagan los límites al conteo VIIRS reservado. Los conteos observados son exactos respecto al archivo, pero su incertidumbre de detección/cobertura es **desconocida**. El intervalo reconciliado solo representa incertidumbre del factor condicional, no incertidumbre total, intervalo predictivo o número de incendios. Con dos años hay muy pocos bloques y el intervalo puede ser discreto o degenerado; no acredita precisión. La evaluación puede empeorar y se informa sin ocultarlo.

### Supuestos y límites pendientes

- Se asume AOI, productos, composición de satélites, filtros y horarios suficientemente comparables; los CSV por sí solos **no permiten verificarlo**. No se controlan nubosidad, ángulo de visión, cobertura de pasada ni cambios de constelación. Se agrupan satélites por sensor; repetir con fuentes homogéneas antes de interpretar diferencias temporales.
- El emparejamiento por timestamp exacto de detección puede fragmentar una pasada que dure varios minutos. La proximidad temporal no demuestra observación de la misma superficie, y el algoritmo voraz puede dejar parejas alternativas sin utilizar.
- Se preserva la separación anual, pero no se conocen eventos independientes; episodios prolongados, dependencia entre años y selección por detección pueden sesgar la evaluación. No hay selección de hiperparámetros ni ajuste sobre el año reservado.
- La cuadrícula tiene bordes rígidos: puntos casi idénticos a ambos lados no coinciden. Las pruebas comprueban ese comportamiento; no demuestran robustez científica a tamaño/origen de celda o tolerancia temporal. Hay que repetir análisis de sensibilidad sobre observaciones reales.
- No se equipara confianza MODIS 0–100 a VIIRS l/n/h, no se compara FRP sin tratamiento del sesgo y no se denominan incendios confirmados a los píxeles de calor.
- No hay referencia independiente ni evidencia observacional de calibración validada. Esta fase implementa un método reproducible para explorar armonización condicional; no demuestra comparabilidad científica de la serie 2000–2026 ni permite uso operacional.

## Tests

```powershell
python -m pytest -q
```

Incluyen los tests originales, casos sintéticos de concordancia, falta de solapamiento, bordes de celda, soporte insuficiente, particiones anuales sin leakage, bootstrap y una prueba de integración Streamlit con los CSV de demostración existentes. Los resultados y particularidades del entorno de ejecución se documentan en [PHASE2_RESULTS.md](PHASE2_RESULTS.md).

## Fuentes (NASA)

- Desafío: https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
- FIRMS: https://www.earthdata.nasa.gov/data/tools/firms
- API de áreas: https://firms.modaps.eosdis.nasa.gov/api/area
- Clave API: https://firms.modaps.eosdis.nasa.gov/api/map_key
- Descarga histórica: https://firms.modaps.eosdis.nasa.gov/download/
- Descripción de MODIS: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html
- Descripción de VIIRS: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html

## Seguridad

No subas la MAP_KEY a GitHub; no la incluyas en capturas, errores ni enlaces compartidos. Consulta únicamente la API oficial de NASA FIRMS.
