# FireSync AI — checklist final de entrega

Revisión del **15 de noviembre de 2026**. Estado: **versión local demostrable preparada**. Actualización posterior: MP4 de **29 segundos** generado automáticamente y verificado en `dist/FireSyncAI_demo_30s.mp4`; informe en `reports/video/video_generation_report.md`. Envío a la competencia y publicación del repositorio no realizados.

## Arranque para presentar

```powershell
.\.venv-phase3\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8513
```

Abrir **http://127.0.0.1:8513/?source=real**. El servidor de revisión quedó ejecutándose en ese puerto y respondió **200 `ok`** en `/_stcore/health`. Si ya está abierto, reutiliza la URL; no intentes arrancar un segundo servidor en el mismo puerto.

Mantener celda 1000 m, confianza MODIS mínima 0, VIIRS sin excluir baja y cohorte SP. El mapa comienza en **25–31 agosto**; los indicadores y calendario representan **1–31 agosto de 2024**. El fondo cartográfico necesita conexión; el procesamiento de CSV locales no necesita API ni MAP_KEY.

## Datos y resultados preservados

- [x] Originales `fire_archive_M-C61_851101.csv` y `fire_archive_SV-C2_851102.csv` intactos; hashes coinciden con el manifiesto de validación.
- [x] Ocho CSV de salida observacional mantienen sus hashes. No se regeneraron ni alteraron los resultados científicos durante el pulido de entrega.
- [x] 2,931 registros MODIS y 13,905 VIIRS: **16,836 observaciones** en la AOI documentada.
- [x] Unión observada: **12,735 celdas-día**, con 650 celdas-día registradas por ambos sensores.
- [x] Concordancia a ±60 min: 41 parejas, 21 días, 51 coincidencias de celda-periodo y Jaccard condicional **0.8538%**.
- [x] 205 timestamps sin pareja y límites del criterio comunicados. Ningún sensor se interpreta como verdad de referencia.
- [x] Un solo año: no se calcula factor de calibración, intervalo reconciliado ni anomalías históricas sin soporte.
- [x] Datos sintéticos permanecen rotulados y separados; no se usaron como observaciones reales.

## Revisión visual de las cinco pestañas

Se recorrieron las cinco pestañas en **Chrome de revisión con perfil separado**, sin utilizar ventanas o perfiles personales. Se capturaron pantallas y se inspeccionaron visualmente el mapa, el calendario, los mensajes y las tablas. El control final del navegador registró **cero excepciones visibles de aplicación y cero eventos de consola recogidos durante esa navegación**.

| Pestaña | Comprobación visual | Resultado |
| --- | --- | --- |
| Mapa de actividad | Teselas CARTO/OSM, puntos por sensor, leyenda, rango 25–31, gráfico diario y explicación del alcance del mapa | Correcto; 2,535 celdas-día en el intervalo inicial, indicadores del mes completo |
| Calendario histórico | Año categórico 2024, meses vacíos, agosto observado, escala de color desde cero y tabla por sensor | Correcto; no aparecen años fraccionarios ni ceros inferidos |
| Anomalías exploratorias | Mensaje de años anteriores insuficientes | Correcto; no se fabrica una anomalía |
| Datos y metodología | Registros, aviso de alcance, manifiestos desplegables, hashes y botones de exportación | Correcto; procedencia y límites visibles |
| Validación MODIS↔VIIRS | Resumen legible de soporte/Jaccard, tablas, falta de entrenamiento y advertencia científica | Correcto; estimaciones sin soporte quedan ausentes |
| Comparación diaria, dentro del calendario | Leyendas MODIS/VIIRS legibles, unidades y huecos de datos | Correcto; se conservan huecos MODIS del 7 y 26 |

Evidencia local en `reports/final_submission_visual/`: `tab_1.png` a `tab_5.png`, `daily.png` y `review.json`. Se excluye de Git. Las capturas de `reports/final_release_visual/` también se inspeccionaron después de aplicar el tema. Los errores transitorios de conexión que produjo reiniciar el servidor quedaron en una revisión anterior; la navegación final se hizo con el servidor activo y el registro de esa sesión limpio.

La herramienta opcional `scripts/visual_review.py` requiere un navegador Chromium y `websocket-client`, ajenos a las dependencias mínimas de la aplicación. En este entorno funcionó conectándose con `--attach` a un Chrome de revisión ya iniciado; los intentos de arrancar headless directamente desde el proceso restringido no funcionaron. Esta herramienta no se necesita para ejecutar FireSync AI.

## Correcciones realizadas para estabilidad y presentación

- [x] Cabecera con problema y alcance; aviso explícito de ausencia de modelo predictivo y calibración validada.
- [x] Indicadores directos de total, celdas-día, MODIS y VIIRS. La cifra multisentor sigue visible como contexto.
- [x] Estados observados/sintéticos visibles en el área principal, además del selector.
- [x] Calendario de un solo año corregido: eje categórico y escala desde cero, sin aparentar años o diferencias numéricas inexistentes.
- [x] Puntos del mapa con tamaño mínimo visible y zoom inicial adecuado en la vista real; no se modificó el cálculo de celdas.
- [x] Leyendas diarias con nombres de sensores y unidades; resumen de concordancia legible antes de la tabla técnica.
- [x] Manifiestos desplegables para facilitar la presentación, conservando toda la auditoría.
- [x] Si faltan o cambian datos de la vista real, se muestra un error y se detiene esa carga; no se cambia a simulación silenciosamente.
- [x] Algoritmos de `core.py`, `calendar.py`, `calibration.py`, ingestión y verificación de datos no modificados en esta etapa de entrega.
- [x] Instalación limpia documentada con build isolation; el asistente Windows incluye setuptools para Python 3.12. Su sintaxis se revisó; la política local sigue impidiendo ejecutar el asistente `.ps1`, por lo que se ofrecen comandos Python directos.

## Pruebas finales

```powershell
.\.venv-phase3\Scripts\python.exe -m pytest -q
.\.venv-phase3\Scripts\python.exe -m compileall -q app.py firesync tests scripts
.\.venv-phase3\Scripts\python.exe -m pip check
.\.venv-phase3\Scripts\python.exe scripts/submission_audit.py
```

- [x] **72 passed in 20.71s**, código 0, frente a las 69 de la validación anterior. Se incluyen dos integraciones opcionales que aquí utilizaron los datos reales.
- [x] Nuevas regresiones: año categórico/escala desde cero, indicadores reales por sensor, carga real ausente sin fallback sintético y reglas de exclusión/redacción de una clave falsa.
- [x] `compileall`: código 0.
- [x] `pip check`: **No broken requirements found**.
- [x] Entorno `.venv-phase3`, Python 3.12.1, sin modificación manual de `sys.path`.

La instalación local usa bibliotecas compatibles ya disponibles y paquetes recuperados de caché. No se certifica una instalación limpia en otro equipo: debe verificarse con conexión y los comandos del README. Streamlit mantiene avisos de deprecación de `use_container_width`; no impiden esta versión, y no se cambió esa API en vísperas de entrega para conservar compatibilidad.

## Git, secretos y empaquetado

- [x] **11 rutas de prueba** verificadas contra las reglas reales de `.gitignore` usando Git en un repositorio temporal aislado.
- [x] Se excluyen CSV mundiales y resultados, incluso `fire_archive_*.csv` accidentalmente colocado en la raíz; ZIP `DL_FIRE_*.zip`, entornos, `.env*`, secretos Streamlit y claves privadas.
- [x] `.env.example` vacío y `.streamlit/config.toml` público permanecen publicables.
- [x] Auditoría heurística de archivos elegibles: **cero patrones de secretos encontrados y cero fallos de exclusión**. Nunca se imprimieron valores privados. No equivale a certificación exhaustiva.
- [ ] Auditar el índice y el historial del repositorio que finalmente se publique: **esta carpeta no contiene `.git`**. No se puede afirmar que un historial remoto esté limpio. Repetir `git status`, `git ls-files` y el control de secretos en el repositorio efectivo; no forzar la inclusión de datos ignorados.
- [x] ZIP de código generado y revisado en `dist/FireSyncAI_submission.zip`; hash y lista de archivos en `dist/submission_manifest.json`. Se comprobó integridad ZIP; los únicos CSV incluidos son los dos de demostración sintética, identificados como tales.

El ZIP es de **código y documentación**, con la demostración sintética rotulada. No contiene originales mundiales, AOI procesada, entornos o credenciales. La demostración real en otro equipo requiere facilitar los originales por separado e importar la AOI según README. No se ha publicado ni enviado el ZIP a terceros.

## Material de presentación

- [x] [README.md](README.md): instalación, arquitectura, datos, metodología, reproducción y limitaciones.
- [x] [METHODOLOGY.md](METHODOLOGY.md): documentación técnica previa preservada para no perder el detalle del método.
- [x] [SUBMISSION.md](SUBMISSION.md): descripción en español e inglés con problema, solución, innovación, impacto potencial y resultados demostrados.
- [x] [DEMO_VIDEO_90S.md](DEMO_VIDEO_90S.md): guion de 90 segundos basado solo en funciones existentes, con tomas y tiempos.
- [x] [REAL_DATA_VALIDATION.md](REAL_DATA_VALIDATION.md): evidencia cuantitativa y hashes.
- [x] Generado el MP4 final solicitado de 29 segundos: Full HD, H.264, 30 FPS, 870 fotogramas decodificados, subtítulos ingleses, transiciones y capturas de la app real. Reproducción y salto al cierre comprobados en Chrome. Sin audio ni ventanas privadas. El guion de 90 segundos se conserva como alternativa previa.
- [ ] Completar equipo/autores, enlaces y campos del formulario oficial. No se inventaron nombres, afiliaciones o impactos medidos.
- [ ] Publicar el repositorio elegido, comprobar los enlaces de acceso y enviar la entrega a la plataforma. Estas acciones no se han realizado.

## Afirmaciones permitidas y límites de la entrega

Se puede demostrar ingestión trazable, exploración regional, calendario observado, comparación diaria y concordancia condicional reproducible. **No** se puede anunciar predicción de IA, calibración científica validada, exactitud satelital demostrada, conteo de incendios únicos, impacto operativo medido ni comparabilidad probada de la serie 2000–2026. Las pruebas de software respaldan comportamiento y reproducción, no validación científica independiente.
