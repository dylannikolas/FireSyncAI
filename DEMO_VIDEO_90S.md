# Video demostrativo — 90 segundos

Guion en español, aproximadamente 200 palabras de locución. Ensayar con cronómetro y respetar los intervalos; hacer los clics mientras se habla. Este archivo es el guion: no se ha producido una grabación.

## Preparación

- Iniciar la aplicación, abrir `http://127.0.0.1:8513/?source=real` y esperar a que cargue el mapa. No mostrar MAP_KEY ni ventanas personales.
- Celda 1000 m, confianza MODIS mínima 0 y VIIRS sin excluir baja. Datos: agosto de 2024, AOI ya recortada.
- La vista inicial del mapa muestra 25–31 de agosto; los indicadores y calendario representan el mes completo. Mantener visible esa distinción.
- No insertar pantallas de funcionalidades futuras ni datos sintéticos durante las tomas.

## Tomas y locución

| Tiempo | Pantalla y acción | Locución |
| --- | --- | --- |
| 00–12 s | Cabecera y etiqueta DATOS OBSERVADOS. | «MODIS y VIIRS observan actividad térmica a distintas resoluciones y horarios. FireSync AI permite compararlos sin confundir detecciones de calor con incendios únicos.» |
| 12–25 s | Indicadores total, MODIS y VIIRS. | «Procesamos originales FIRMS de agosto de 2024 en una zona de la Amazonía peruana: dieciséis mil ochocientas treinta y seis observaciones. Conservamos sensor, fechas, versiones y hashes.» |
| 25–40 s | Mapa: rango 25–31, leyenda y acercamiento suave. | «El mapa agrega puntos en celdas comunes y días UTC. Aquí exploramos la última semana; los indicadores resumen el mes. Los colores distinguen sensores y coincidencias diarias, sin identificar incidentes independientes.» |
| 40–55 s | Calendario de agosto; bajar a comparación diaria. | «El calendario muestra doce mil setecientas treinta y cinco celdas-día en la unión observada. La comparación diaria conserva huecos: un sensor sin registros no demuestra ausencia de actividad.» |
| 55–69 s | Validación: resumen de parejas y Jaccard. | «Al alinear horarios a sesenta minutos obtenemos cuarenta y una parejas y un Jaccard condicional de cero coma ochenta y cinco por ciento. No es exactitud: ningún sensor se usa como verdad.» |
| 69–80 s | Anomalías: mensaje de años insuficientes; validación: falta de calibración. | «Con un solo año no calculamos anomalías históricas ni una calibración validada. La aplicación indica que falta información; no inventa estimaciones.» |
| 80–90 s | Datos y metodología: tabla, manifiesto y exportación. | «Los registros, parámetros y resultados son auditables y exportables. Ofrecemos exploración reproducible; no un modelo predictivo de inteligencia artificial ni una alerta operativa.» |

## Antes de grabar

Comprobar conexión para las teselas; el procesamiento local no necesita API. Si no carga el fondo, no editar una toma para aparentar que cargó. Mantener el origen real seleccionado. La normalización experimental existe en el código, pero no mostrar un factor para este único año: la aplicación lo deja sin información. Grabar y subir el video son pasos humanos pendientes.
