# FireSync AI — descripción para NASA Space Apps

Texto para los campos del formulario. No se ha publicado ni enviado desde esta sesión. Los resultados corresponden a una AOI y un mes, no a desempeño global.

## Español

### Resumen

**FireSync AI transforma detecciones térmicas MODIS y VIIRS de NASA FIRMS en mapas y calendarios comparables, manteniendo visible su origen y los límites de la comparación.** El prototipo demuestra ingestión trazable y concordancia exploratoria con 16,836 observaciones de agosto de 2024 en una AOI de la Amazonía peruana. El nombre del proyecto no implica un modelo predictivo de inteligencia artificial: esa capacidad no está implementada ni evaluada.

### Problema

MODIS y VIIRS observan a distintas resoluciones, horarios y condiciones. Sumar sus puntos o comparar recuentos sin contexto puede confundir cambios de observación con cambios de actividad. Un píxel de calor no identifica por sí solo un incendio independiente y un día sin registros no demuestra ausencia de actividad.

### Solución

FireSync AI importa CSV históricos y permite consultas FIRMS opcionales. Valida producto, plataforma, fechas y coordenadas; conserva confianza específica de cada sensor, metadatos y hashes de los originales. Agrega observaciones a una cuadrícula de igual área y día UTC. Cinco pestañas permiten explorar mapa, calendario mensual y comparación diaria, historia relativa cuando existe, trazabilidad y concordancia espacial-temporal. Los datos sintéticos permanecen separados de las observaciones aportadas.

### Innovación

El aporte es una comparación reproducible que explicita lo que se puede y no se puede concluir. Distingue celdas-día de celdas-periodo, compara sensores sin declarar a ninguno como verdad y reserva años completos para evaluar una normalización experimental cuando hay soporte. Evita publicar una serie reconciliada o intervalos cuando faltan datos. No presentamos estas decisiones como un algoritmo científicamente novedoso ya validado.

### Resultados demostrados

Con originales aportados por el usuario como descargas FIRMS, se verificaron 2,931 detecciones MODIS Terra/Aqua C6.1 y 13,905 VIIRS S-NPP C2, del 1 al 31 de agosto de 2024. La cuadrícula de 1 km produjo una unión observada de 12,735 celdas-día. A ±60 minutos se obtuvieron 41 parejas temporales en 21 días y 51 coincidencias de celda-periodo; el Jaccard condicional fue 0.8538%. La baja concordancia y su sensibilidad a celda/ventana se informan. Un solo año no permite calibración por años independientes. Las pruebas automatizadas y los hashes reproducen la ingestión y estos conteos; no prueban exactitud satelital.

### Impacto y límites

El prototipo puede apoyar a estudiantes, investigadores y analistas a inspeccionar actividad térmica regional y preparar comparaciones auditables. No se ha medido impacto operativo o reducción de daños. Faltan cobertura válida, nubes, referencia independiente y varios años comparables antes de validar una corrección de detectabilidad. No ofrece predicción, clasificación de incendios confirmados ni alertas para decisiones de emergencia.

## English

### Overview

**FireSync AI turns NASA FIRMS MODIS and VIIRS thermal detections into comparable maps and calendars while preserving provenance and the limits of comparison.** The prototype demonstrates traceable ingestion and exploratory agreement analysis with 16,836 observations from August 2024 in an approximate Peruvian Amazon study area. The project name does not imply a predictive artificial intelligence model: that capability has not been implemented or evaluated.

### Problem

MODIS and VIIRS observe at different resolutions, times and conditions. Adding their points or comparing counts without context can confuse changes in observation with changes in activity. A heat-detection pixel does not identify an independent fire, and a day without records does not establish that no fire occurred.

### Solution

FireSync AI imports historical CSV files and supports optional FIRMS queries. It checks product, platform, dates and coordinates, preserving sensor-specific confidence, metadata and original-file hashes. Observations are aggregated to a common equal-area grid and UTC day. Five tabs provide an activity map, monthly calendar and daily comparison, historical relative activity when supported, provenance, and spatial-temporal agreement. Synthetic demonstration data remain visibly separate from supplied observations.

### Innovation

The contribution is a reproducible comparison that states what can and cannot be inferred. It distinguishes cell-days from cell-periods, compares sensors without treating either as ground truth, and reserves complete years to evaluate experimental normalization when support is sufficient. It withholds reconciled estimates and intervals when information is missing. We do not claim a scientifically novel algorithm that has already been validated.

### Demonstrated results

Using files supplied by the user as original FIRMS downloads, we verified 2,931 MODIS Terra/Aqua Collection 6.1 detections and 13,905 VIIRS S-NPP Collection 2 detections from August 1–31, 2024. A 1 km grid yielded an observed union of 12,735 active cell-days. With a ±60-minute window, the method produced 41 timestamp pairs across 21 days and 51 matching cell-periods, with a conditional Jaccard score of 0.8538%. Low agreement and sensitivity to grid/window choices are reported openly. A single year cannot support calibration with independent training and evaluation years. Automated tests and hashes reproduce ingestion and these counts; they do not establish satellite accuracy.

### Potential impact and limitations

The prototype can help students, researchers and analysts inspect regional thermal activity and prepare auditable comparisons. Operational impact or damage reduction has not been measured. Valid coverage, cloud information, independent reference data and multiple comparable years are still required to validate detectability correction. The application provides no forecast, confirmed-fire classification or emergency decision alert system.

## Evidencia y fuentes / Evidence and sources

- [Validación real y hashes / Real-data validation and hashes](REAL_DATA_VALIDATION.md).
- [Revisión y pruebas finales / Final review and tests](FINAL_SUBMISSION_CHECKLIST.md).
- [Video final de 29 segundos / Final 29-second video](dist/FireSyncAI_demo_30s.mp4) e [informe de generación / generation report](reports/video/video_generation_report.md). Artefactos locales entregados por separado del repositorio.
- [Archivo NASA FIRMS / NASA FIRMS archive](https://firms.modaps.eosdis.nasa.gov/download/) y [documentación de archivos / file documentation](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt).

## No afirmar / Claims to avoid

No describir el total como incendios únicos, el Jaccard como exactitud o la unión observada como corrección validada. No anunciar predicción de IA, detección de incendios confirmados, impacto operativo medido o validación de toda la serie 2000–2026. Las pruebas automatizadas verifican software y reproducibilidad, no exactitud científica. Consulta el número final de pruebas en la checklist.
