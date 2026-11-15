# Históricos: entrada local

El usuario aportó originales FIRMS mundiales de agosto de 2024 en `data/raw/`;
su validación y conteos se documentan en [REAL_DATA_VALIDATION.md](../REAL_DATA_VALIDATION.md).
Los originales y sus derivados locales se excluyen de Git. Los archivos
`demo_*.csv` de esta carpeta son **sintéticos** y nunca deben copiarse al
directorio de archivos oficiales ni presentarse como datos reales.

Guarda tus CSV originales sin editarlos en:

```text
data/raw/modis/fire_archive_M-C61_....csv
data/raw/viirs_snpp/fire_archive_SV-C2_....csv
```

También se reconocen los archivos directamente en `data/raw/` con los prefijos
de producto anteriores, como `fire_archive_M-C61_851101.csv` y
`fire_archive_SV-C2_851102.csv`; no es necesario moverlos.

Ambas rutas están excluidas de Git. En la aplicación elige **Históricos MODIS
C6.1 / S-NPP C2** y selecciona los archivos locales o carga los originales en
los dos controles de subida. La colección y plataforma declaradas se comprueban
fila por fila, pero el programa no puede certificar la autenticidad de un CSV
local. Conserva el correo/recibo de descarga oficial junto a tus archivos fuera
del repositorio.

Procedimiento, fuentes, comandos de importación y límites en
[README.md](../README.md) y resultados reales de esta ejecución en
[REAL_DATA_VALIDATION.md](../REAL_DATA_VALIDATION.md). El informe inicial,
previo a los archivos aportados, se conserva en [PHASE3_RESULTS.md](../PHASE3_RESULTS.md).
