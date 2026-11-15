# Validación con observaciones FIRMS — agosto de 2024

Ejecutada el **15 de noviembre de 2026**. Se procesaron los dos archivos aportados por el usuario como originales NASA, sin descargar nuevas observaciones, modificar originales ni incorporar registros sintéticos. **Esta es una validación de ingestión y un diagnóstico de concordancia observada; no una calibración científicamente validada.**

## Integridad y procedencia

| Archivo | Bytes | Filas mundiales | Filas en la AOI | Satélites en la AOI | Versión original |
| --- | ---: | ---: | ---: | --- | --- |
| `fire_archive_M-C61_851101.csv` | 62,113,429 | 773,697 | **2,931** | Aqua: 2,473; Terra: 458 | `61.03` |
| `fire_archive_SV-C2_851102.csv` | 291,375,162 | 3,582,707 | **13,905** | SNPP: 13,905 | `2` |

SHA-256 de los bytes originales, comprobados antes y después de la importación:

```text
fire_archive_M-C61_851101.csv
42e978c34438da0cf74ec88a4266882298736d895bb46d65994120ee3b096cc4

fire_archive_SV-C2_851102.csv
169076a1579d38adc3ebbeefd67ed6fe793a32ff16f29f41180661ab0401ee96
```

Ambos CSV se parsearon completos, por bloques de 100,000 filas. Tienen las mismas 15 columnas:

```text
latitude, longitude, brightness, scan, track, acq_date, acq_time,
satellite, instrument, confidence, version, bright_t31, frp, daynight, type
```

En ambos archivos, las fechas mundiales son exclusivamente **2024-08-01 a 2024-08-31**, con filas en los 31 días. No se encontraron fechas, horas, coordenadas, valores de confianza, plataforma o colección inválidos según los criterios del importador. Todas las exclusiones fueron geográficas: **770,766 MODIS** y **3,568,802 VIIRS** fuera de la AOI. No hubo duplicados de las claves de observación aceptadas ni duplicados entre archivos.

Los nombres siguen las familias `fire_archive_M-C61_*` y `fire_archive_SV-C2_*` descritas en el [Readme oficial FIRMS](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt). Los dos Readme locales contienen un enlace a esa documentación. No hay en esos archivos una firma, checksum publicado por NASA o recibo de solicitud que permita autenticar externamente los CSV: el origen NASA está **declarado por el usuario** y sus metadatos son consistentes. Los hashes permiten comprobar que se siguen procesando los mismos bytes; no certifican por sí solos el origen remoto. Se mantiene la etiqueta interna `user_supplied_unverified`, distinta de `synthetic` y `nasa_api`.

## Compatibilidad corregida y criterios

La ingestión anterior habría rechazado estas observaciones por dos restricciones incompletas del prototipo:

- El archivo MODIS lleva `version=61.03`. Se añadió ese valor explícito a los identificadores aceptados para el producto declarado C6.1, conservando `61.03` en cada observación y manifiesto. No se admiten indiscriminadamente revisiones o colecciones desconocidas.
- El archivo S-NPP lleva `instrument=SNPP`, además de `satellite=SNPP`. Se admite este identificador de exportación para el producto S-NPP declarado y se normaliza el sensor a VIIRS. Se conservan `instrument_original=SNPP` y el satélite original. NOAA-20/21 siguen rechazándose en el importador S-NPP.

Estas correcciones responden al esquema observado en los archivos aportados, no a una búsqueda de parámetros para obtener los conteos esperados. Las pruebas de regresión usan pequeños fixtures explícitamente artificiales, separados de la validación local real.

AOI: oeste **−76.5**, sur **−12.5**, este **−72**, norte **−7**. Límites geográficos y fechas inclusivos; coordenadas WGS84 y tiempos UTC. Es una caja aproximada en Amazonía peruana, no el límite completo de un bioma o una región administrativa.

Se seleccionó procesamiento **SP**, celda EPSG:6933 de **1000 m**, confianza MODIS mínima **0**, sin excluir VIIRS `l`, y sin filtro silencioso por `type`. Se preservan satélite, colección, resolución nominal (MODIS 1000 m / VIIRS 375 m), versión, fecha/hora original, fila original y campos auxiliares disponibles. No se utiliza FRP para armonizar.

Los conteos coinciden **exactamente**, sin tolerancia ni ajuste forzado, con los indicados por el usuario: **2,931 MODIS + 13,905 VIIRS = 16,836 registros observados**.

## Calendario y comparación diaria

| Agosto de 2024, AOI | Resultado observado |
| --- | ---: |
| Detecciones MODIS | 2,931 |
| Detecciones VIIRS S-NPP | 13,905 |
| Celdas-día MODIS, 1 km | 2,804 |
| Celdas-día VIIRS, 1 km | 10,581 |
| Unión de celdas-día observadas | **12,735** |
| Celdas-día registradas por ambos sensores | **650** |
| Días con registros MODIS / VIIRS en la AOI | **29 / 31** |

Se cumple `2804 + 10581 − 650 = 12735`. La coincidencia diaria solo exige la misma celda y día UTC; no es una coincidencia de adquisición cercana en el tiempo.

No hay registros MODIS en la AOI los días **7 y 26 de agosto**. La comparación diaria conserva esos valores como **sin información**, no como ceros inferidos de actividad. Los 31 días con registros VIIRS tampoco demuestran cobertura válida o cielo despejado de toda la AOI.

Algunos puntos de la comparación diaria, sin sustituir la tabla completa exportada:

| Día UTC | Detecciones MODIS | Detecciones VIIRS | Celdas-día MODIS | Celdas-día VIIRS |
| --- | ---: | ---: | ---: | ---: |
| 2024-08-01 | 8 | 191 | 8 | 145 |
| 2024-08-07 | Sin información | 183 | Sin información | 153 |
| 2024-08-15 | 445 | 692 | 423 | 480 |
| 2024-08-23 | 170 | 1,085 | 160 | 819 |
| 2024-08-26 | Sin información | 39 | Sin información | 28 |
| 2024-08-31 | 16 | 806 | 14 | 572 |

Las diferencias no cuantifican incendios únicos ni sensibilidad real. Se conservó todo `type`: en la AOI hay MODIS `0`: 2,902 y `2`: 29; VIIRS `0`: 13,842, `2`: 45 y `3`: 18. Por tanto, tampoco se presenta el total como exclusivamente fuegos de vegetación confirmados. VIIRS contiene 12,635 registros `n`, 685 `h` y 585 `l`; no se equipararon estas categorías con la confianza numérica MODIS.

## Concordancia espacial y temporal

Método de fase 2 sin cambiar su criterio: timestamps MODIS en orden cronológico, timestamp VIIRS disponible más cercano dentro de **±60 minutos**, pareja uno a uno, sin reutilizar timestamps ni cruzar años. Se comparan conjuntos de celdas de 1 km dentro de cada pareja. Cada timestamp proviene de detecciones, no de una huella de pasada verificada.

| Métrica condicional, 1 km y ±60 minutos | Resultado |
| --- | ---: |
| Timestamps observados MODIS / VIIRS | 126 / 161 |
| Parejas temporales | **41** |
| Días con parejas | **21** |
| Timestamps sin pareja, ambos sensores | **205** |
| Desfase de parejas: mediana / media / máximo | 17 / 20.90 / 60 minutos |
| Celdas-periodo MODIS en parejas | 1,172 |
| Celdas-periodo VIIRS en parejas | 4,852 |
| Coincidencias de celda-periodo | **51** |
| Solo MODIS / solo VIIRS en parejas | 1,121 / 4,801 |
| Jaccard: `51 / (1172 + 4852 − 51)` | **0.8538%** |
| VIIRS dado MODIS: `51 / 1172` | **4.3515%** |
| MODIS dado VIIRS: `51 / 4852` | **1.0511%** |

Las fracciones son condicionales a las parejas seleccionadas, sin sensor de verdad. **No son exactitud, sensibilidad real ni tasas de falsos positivos.** Las 51 coincidencias de celda-periodo no deben compararse como si fueran la misma unidad que las 650 celdas-día multisentor.

Sensibilidad exploratoria predefinida, sin elegir una configuración como «ganadora»:

| Celda | Tolerancia | Parejas | Días con parejas | Coincidencias | Jaccard |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 km | ±30 min | 29 | 14 | 48 | 1.0784% |
| 1 km | ±60 min | 41 | 21 | 51 | 0.8538% |
| 1 km | ±90 min | 60 | 26 | 137 | 1.3491% |
| 2 km | ±30 min | 29 | 14 | 85 | 2.1756% |
| 2 km | ±60 min | 41 | 21 | 90 | 1.7218% |
| 2 km | ±90 min | 60 | 26 | 205 | 2.2949% |
| 5 km | ±30 min | 29 | 14 | 91 | 2.7778% |
| 5 km | ±60 min | 41 | 21 | 100 | 2.2584% |
| 5 km | ±90 min | 60 | 26 | 247 | 3.2876% |

Cambiar tolerancia cambia también qué timestamps se emparejan: estos resultados no son un experimento controlado de cambio de sensibilidad física del sensor. Un tamaño de celda mayor puede aumentar coincidencias por agregación, sin demostrar mayor exactitud.

## Límites y estado de calibración

- Solo existe agosto de **2024**: cero años de entrenamiento y ningún año posterior independiente disponible. Se mantiene **«insuficiente información»** para calibración; factor, intervalos bootstrap, conteos reconciliados y MAE reservado quedan ausentes. No se dividieron días aleatoriamente para fingir validación anual.
- La baja concordancia describe este criterio y estos archivos; no prueba que un sensor esté equivocado. El emparejamiento voraz de timestamps exactos puede fragmentar pasadas de varios minutos o seleccionar dos fragmentos que observaron partes distintas de la AOI. No es un emparejamiento óptimo de huellas de satélite.
- Las 205 adquisiciones sin pareja quedan fuera del denominador de concordancia. Hay sesgo de selección por días/horarios con detecciones en ambos sensores. No hay máscara de nubes, cobertura negativa válida, ángulo de visión ni referencia independiente.
- No se verificó externamente el subidentificador de procesamiento `61.03` ni una firma del archivo; se conserva tal cual bajo el producto C6.1 declarado y se documenta esta compatibilidad explícita.
- La cuadrícula tiene bordes rígidos y resolución común distinta de la resolución nativa VIIRS. No se equipara FRP entre sensores ni confianza numérica y categórica.
- Los resultados son **observaciones de píxeles de calor y sus agregaciones**, no cantidades de incendios independientes, superficies quemadas ni incidentes confirmados.

## Resultados guardados y cambios de código

Directorio local **`data/processed/real_2024_08/`**, excluido de Git:

- `observations.csv`: 16,836 filas con procedencia y campos originales.
- `manifest.json`: auditoría mundial por archivo, conteos, exclusiones, fechas, versiones, hashes de originales y salidas, parámetros y versiones de software.
- `calendar.csv`: agosto observado por sensor y unión.
- `daily_comparison.csv`: 31 fechas, registros/celdas por sensor y solapamiento diario.
- `overlap_pairs.csv`, `overlap_monthly.csv`: 41 parejas y sus métricas.
- `evaluation.csv`, `calendar_experimental.csv`: insuficiencia de soporte y calendario experimental vacío con cabecera.
- `sensitivity.csv`: las nueve configuraciones de celda/tolerancia.

La primera ejecución también produjo `data/processed/real_2024_08_run01/`; el directorio sin sufijo es la entrega definitiva con comparación diaria, sensibilidad y hashes de salidas.

Cambios: `firesync/history.py` (formatos de archivo, lectura por bloques, auditoría, descubrimiento de archivos en raíz y salidas), `firesync/calendar.py` (comparación diaria), `firesync/validated_data.py` (carga de resultados observados y comprobación de hashes), `app.py` (vista real preparada, caché de importación local y gráficos diarios), `tests/test_real_ingestion.py` (regresiones e integración real opcional) y documentación. Se conservan los métodos de fase 2 y los CSV originales.

## Pruebas y comprobación de interfaz

Entorno `.venv-phase3`, Python 3.12.1, sin modificar `sys.path`.

```powershell
.\.venv-phase3\Scripts\python.exe -m pytest -q
```

Resultado final: **69 passed in 27.08s**, código 0. Incluye las 61 pruebas previas, seis nuevos casos con fixtures artificiales y **dos integraciones con los datos reales locales**. Estas últimas verifican hashes, conteos, calendario, concordancia, ausencia de factor, mapa/heatmap serializados y comparación diaria en Streamlit. En una copia sin originales/resultados locales, esas dos pruebas se omiten explícitamente; no se sustituyen por datos inventados. También pasaron `python -m compileall -q app.py firesync tests scripts` y `python -m pip check` (sin dependencias rotas), ejecutados con el Python del entorno. Una comprobación final confirmó hashes intactos de los dos originales y de los ocho CSV de salida.

AppTest verificó la carga real sin excepciones, 16,836 detecciones y 12,735 celdas-día, mapa PyDeck, calendario Plotly, comparación diaria de 31 fechas y mensaje sin información en la vista reconciliada. El servidor local respondió `200 ok` en `/_stcore/health`. También se abrió la URL real en Edge y se observó el encabezado con conteos y procedencia. La comprobación automática verifica generación de mapa/gráficos; no certifica la descarga de todas las teselas del mapa base en el navegador.

El mapa conserva el límite visual de **10,000 celdas** con advertencia; los conteos, gráficos y CSV usan las 12,735 celdas-día completas. Filtra fechas para inspeccionar menos puntos. No se eliminó este límite de fase 1 ni se presentó la selección visual como todo el conjunto.

## Reproducir, ejecutar y demostrar

Desde la raíz del proyecto, con el entorno ya preparado:

```powershell
.\.venv-phase3\Scripts\python.exe -m firesync.history --modis data/raw/fire_archive_M-C61_851101.csv --viirs data/raw/fire_archive_SV-C2_851102.csv --start 2024-08-01 --end 2024-08-31 --bbox -76.5 -12.5 -72 -7 --sensitivity --output data/processed/real_2024_08_repro01
.\.venv-phase3\Scripts\python.exe -m pytest -q
.\.venv-phase3\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8513 --browser.gatherUsageStats false
```

La CLI exige un directorio de salida **nuevo** y no sobrescribe resultados existentes. La vista preparada utiliza `data/processed/real_2024_08/`, creado durante esta validación; si no existe en otra copia, genera ese directorio con el mismo comando cambiando `--output`. Para una instalación nueva consulta los comandos Windows de [README.md](README.md).

Abre **http://127.0.0.1:8513/?source=real** o elige **Observaciones FIRMS · agosto 2024 (AOI)** en el selector. Esa vista carga exclusivamente las observaciones reales aportadas y verifica hashes de los originales y todas las salidas; un original o resultado modificado produce error, sin recurrir a datos sintéticos.

Demostración sugerida:

1. Enseña la fuente, fechas y conteos; explica que son detecciones observadas, no incendios únicos.
2. Abre el mapa y reduce el intervalo para explorar las celdas sin alcanzar el límite visual.
3. En Calendario selecciona MODIS y VIIRS; enseña agosto y los gráficos diarios. Señala los huecos MODIS del 7 y 26 como ausencia de registros, sin inferir ausencia de incendios.
4. En Validación MODIS↔VIIRS muestra las 41 parejas, el Jaccard condicional y el soporte; distingue celda-periodo de celda-día.
5. Enseña «insuficiente información» para calibración y explica que hacen falta al menos dos años anteriores de ajuste y otro independiente para evaluar, además de controlar cobertura y sesgos.
6. En Datos y metodología muestra hashes, versiones y descarga observaciones/calendario. La demostración sintética sigue disponible por separado.
