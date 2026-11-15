# Resultados de fase 2 — 2026-11-15

## Alcance entregado

| Archivo | Cambio |
| --- | --- |
| `firesync/calibration.py` | Diagnóstico mensual por AOI en celdas comunes, emparejamiento temporal uno a uno, soporte, normalización mensual experimental, evaluación anual y bootstrap por años. |
| `app.py` | Quinto tab «Validación MODIS↔VIIRS», recorte AOI, tolerancia, tablas auditables y exportación. No aplica factores a las visualizaciones de fase 1. |
| `tests/test_calibration.py` | 17 casos ejecutados, todos con datos artificiales explícitos. |
| `tests/test_app.py` | Integración Streamlit: cinco tabs, advertencia sintética, AOI sin parejas e indicadores de fase 1 conservados al cambiar el recorte de validación. |
| `README.md` | Método, ecuación, umbrales, denominadores, incertidumbre, supuestos no verificables y límites científicos. |
| `.gitignore` | Excluye el entorno auxiliar `.venv-phase2/`. |
| `PHASE2_RESULTS.md` | Este informe de ejecución y límites. |

Se leyeron `CODEX_TASKS.md`, README, núcleo, cliente NASA, aplicación y tests originales antes de implementar. No había módulo de calibración ni tests de fase 2. No se encontraron `AGENTS.md` en el proyecto ni en sus dos directorios superiores. `git status --short` informó que esta carpeta no es un repositorio Git: no fue posible obtener un diff contra un commit. No se reescribieron el núcleo, cliente NASA, scripts de demostración, datos ni tests originales; los cambios en la aplicación son aditivos (importación, quinto tab y su contenido).

## Ejecución real de pruebas

El `.venv` existente apunta a Python 3.11 de WindowsApps que ya no puede iniciarse. El Python predeterminado es 3.12.1 y no tiene pytest instalado. Se creó un entorno auxiliar `.venv-phase2`, sin alterar el original; la instalación con `pip install -r requirements.txt` falló por bloqueo de sockets (`WinError 10013`). Ese entorno auxiliar quedó sin las dependencias solicitadas y no se usó para validar.

Fue posible ejecutar con las dependencias ya disponibles en Python 3.12 y añadir **al final** de `sys.path` el directorio del entorno anterior para localizar pytest y sus dependencias Python. NumPy, pandas, pyproj y Streamlit se cargaron de la instalación de Python 3.12; no se intentó cargar sus extensiones cp311 en Python 3.12. No se modificaron instalaciones globales.

Comando de referencia inicial:

```powershell
python -c "import sys; sys.path.append(r'.venv/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(['tests/test_core.py','-q']))"
```

Resultado: **5 passed in 0.25s** (tests originales).

Comando completo final, desde la raíz del proyecto:

```powershell
python -c "import sys; sys.path.append(r'.venv/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(['-q']))"
```

Resultado: **23 passed, 3 warnings in 8.50s**, código de salida 0. Incluye 5 tests originales, 17 casos de calibración y 1 integración de interfaz. Las tres advertencias de pytest proceden de `pd.Timedelta(days=60)` en la visualización original, debido a la combinación NumPy/pandas instalada. Streamlit también emite avisos de futura sustitución de `use_container_width` y de contexto en AppTest. No se ocultaron estos avisos ni se cambiaron visualizaciones básicas para eliminarlos.

```powershell
python -m compileall -q app.py firesync tests
```

Resultado: código de salida 0.

Versiones observadas: Python 3.12.1, Streamlit 1.52.2, NumPy 2.5.4, pandas 2.2.3, pyproj 3.7.1 y pytest 9.2.0. Esta ejecución con dependencias locales no sustituye una instalación limpia de `requirements.txt`, que no pudo verificarse por la restricción de red. En un entorno funcional con dependencias instaladas, el comando normal sigue siendo `python -m pytest -q`.

## Qué se verificó

- Concordancia perfecta de una celda y invariancia a registros repetidos; no coincidencia espacial sin etiquetar un sensor como verdad.
- Exclusión de fechas anteriores a 2012, años sin solapamiento, timestamps separados más que la tolerancia y entrada vacía.
- Tolerancia inclusiva, cruce de medianoche/mes y prohibición de emparejar a través de años; cada adquisición solo se usa una vez.
- Discontinuidad esperada alrededor de bordes de cuadrícula, incluidos índices negativos.
- Factor conocido 0.5 en un fixture artificial, intervalos bootstrap, conteos reservados y MAE antes/después.
- Alterar las detecciones del año reservado no cambia el factor ni su bootstrap; puede empeorar el error reservado.
- Factores independientes por mes, variabilidad entre años, aislamiento de AOIs y recorte geográfico.
- Soporte insuficiente devuelve razones y valores ausentes; entrada original intacta y parámetros inválidos rechazados.
- Apertura e interacción de la aplicación con la demostración existente, sin excepciones y sin cambiar indicadores básicos al recortar únicamente la validación.

## Inspección de la demostración existente — exclusivamente sintética

Con los CSV de demostración originales, sin filtros de confianza, celda de 1000 m y tolerancia ±60 minutos: **1046 registros artificiales**, **291 parejas temporales**, **58 filas año-mes**, **82 adquisiciones sin pareja**, ningún registro excluido. Once meses del calendario devolvieron «insuficiente información». Agosto superó los umbrales prácticos: 26 días y 28 coincidencias de entrenamiento, 17 días y 26 coincidencias reservados. Esto solo ejercita el flujo de software; **no valida ninguna calibración satelital**. No se generaron nuevos CSV ni se alteraron los existentes.

## Límites reales

No se descargaron observaciones NASA, no se utilizaron credenciales y no se cambiaron claves. Las únicas solicitudes externas intentadas fueron las de instalación de dependencias, fallidas por la restricción de red.

No se dispone de cobertura válida, nubes, huellas de pasada, control de constelaciones ni referencia independiente. La coincidencia temporal/espacial y los días emparejados son condicionales a detecciones cargadas, no evidencia de días despejados ni de incendios confirmados. El ajuste es exploratorio, no una corrección física de sensibilidad. Los IC solo propagan incertidumbre del factor con pocos años disponibles; no incorporan sesgos sistemáticos ni incertidumbre de detección/cobertura. Un resultado fuera de muestra o un intervalo estrecho en fixtures sintéticos no acredita exactitud científica.

Antes de afirmar comparabilidad de una serie MODIS–VIIRS se necesitan observaciones reales con procedencia y cobertura verificables, análisis de sensibilidad de cuadrícula/ventanas, productos homogéneos y evaluación independiente por regiones y años. No se extrapolan los factores a años sin solapamiento ni se afirma una serie 2000–2026 científicamente validada.
