# GitHub prepublication review

Estado: Git inicializado en main. Sin commit, remoto ni publicacion. Archivos candidatos SIN staging: git add fallo porque el entorno no permite escribir .git/index.lock (Permission denied).

## Verificaci?n

- Suite completa: **72 passed in 101.93s**. Despu?s de corregir la auditor?a y a?adir una regresi?n para el ?ndice vac?o/video p?blico: **3 passed in 1.30s** en `tests/test_submission.py` (dos casos existentes y uno nuevo; 73 casos ?nicos aprobados entre ambas ejecuciones).
- `python -m pip check`: `No broken requirements found.` Validaci?n realizada con `.venv-phase3`, no con una instalaci?n limpia.
- Auditor?a heur?stica de patrones de credenciales y reglas Git: sin hallazgos en candidatos; no imprime valores secretos. No equivale a una garant?a de ausencia de informaci?n privada ni a un an?lisis de vulnerabilidades de dependencias.
- B?squeda adicional en c?digo y documentaci?n: sin rutas personales `C:\Users`, OneDrive, correos de proveedores comunes ni asignaciones sospechosas de claves.
- MP4: decodificaci?n completa de **870/870 fotogramas**, 1920?1080, 30 FPS, **29 segundos**, 1,819,322 bytes.
- SHA-256 del MP4: `90e77c2606f4a4523faa7ea5d64c406d79423e7d25617ef4092a546ee67dc02e`.

## Inventario y privacidad

Lista completa: [GITHUB_FILES.txt](GITHUB_FILES.txt). Incluye c?digo, pruebas, scripts, documentaci?n, configuraci?n p?blica, `.env.example` con clave vac?a, dos CSV de demostraci?n sint?ticos y `videos/FireSyncAI_demo_30s.mp4`.

Excluidos: `data/raw/`, `data/processed/`, `.venv*/`, wheels, cach?s, `dist/`, ZIP, `reports/` (incluidos perfiles locales de navegador), `.env` y variantes privadas, secretos Streamlit, certificados/claves y archivos habituales de credenciales. No se borraron datos locales.

La documentaci?n conserva resultados agregados observados, nombres de productos FIRMS, AOI y hashes para reproducibilidad; los CSV originales no se incluyen. El video contiene la demostraci?n de la aplicaci?n. El propietario debe revisar estos contenidos antes de autorizar su publicaci?n.

## Revisi?n previa a publicar

```powershell
git ls-files --others --exclude-standard
# Tras revisar y desde un entorno con permiso de escritura sobre .git:
git add -- .
git diff --cached --stat
git diff --cached --name-only
.\.venv-phase3\Scripts\python.exe scripts/submission_audit.py
```

No se ejecut? `git push` ni se cre? un repositorio remoto. El primer commit y la publicaci?n quedan pendientes de revisi?n.
