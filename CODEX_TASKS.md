# Prompt para Codex — Fase 2 (trabajo paralelo)

Abre esta carpeta en VS Code y ejecuta Codex. Pega el texto completo que sigue:

---

Estoy participando en NASA Space Apps Challenge 2026, desafío 'Harmonization of MODIS and VIIRS Hot Spots'. Tenemos un MVP Streamlit funcionando en este repo `FireSyncAI`. **No reescribas ni elimines las funciones o pruebas existentes sin necesidad**. Lee primero `README.md`, `firesync/core.py`, `firesync/nasa.py`, `app.py`, y ejecuta `python -m pytest -q`.

Tu tarea exclusiva de la fase 2 es implementar la **validación científica y la calibración exploratoria de la serie MODIS–VIIRS**, sin afirmaciones de exactitud no demostradas:

1. Crea el módulo `firesync/calibration.py`. Usando únicamente registros con superposición temporal (2012+) calcula un diagnóstico mensual, por zona/AOI, de los sesgos de detección. NO apliques ingenuamente un cociente global de puntos. Trabaja en celdas comunes y ventanas de observación alineadas temporalmente (por ejemplo +/- 60 minutos para concordancia), con métricas de coincidencia de celdas, precisión/recall condicional **sin interpretar un sensor como verdad**, número de días/periodos válidos, variabilidad entre años y soporte muestral.
2. Implementa un método experimental y claramente rotulado de normalización entre sensores, SOLO si hay datos de solapamiento suficientes, incorporando incertidumbre e intervalos de confianza por bootstrap si es posible. Si los datos disponibles no permiten la calibración, muestra 'insuficiente información' y explica por qué.
3. Crea `tests/test_calibration.py` con casos sintéticos: misma detección en ambos sensores, detecciones no coincidentes, sin años de solapamiento, y coordenadas cercanas a límites de celdas. Evita leakage: particiona evaluación por años (entrenamiento vs validación), no mezcla fechas aleatorias de un mismo evento.
4. Integra un tab nuevo 'Validación MODIS↔VIIRS' en `app.py` con números observados/reconciliados por sensor y su incertidumbre. No debe modificar las visualizaciones básicas de la fase 1.
5. Documenta cuidadosamente en `README.md` qué supuestos sí/NO se cumplen. No equipares confianza MODIS 0–100 a VIIRS l/n/h, ni compares FRP sin tratamiento de sesgo, ni llames incendios confirmados a 'píxeles de calor'.
6. Corre tests y entrega resumen de archivos modificados, resultados y limitaciones reales. No inventes datos NASA, no uses credenciales en el código y no realices llamadas externas sin necesidad. No modifiques ni subas claves de usuario.

Meta: un método demostrable y honesto para justificar el término 'armonización', no solo superponer dos capas en el mapa.

---
