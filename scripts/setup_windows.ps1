param(
    [string]$Python = "python",
    [string]$VenvPath = ".venv-phase3",
    [switch]$UseSystemPackages,
    [string]$Wheelhouse = ""
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $venvPython = Join-Path $VenvPath "Scripts/python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $venvArguments = @("-m", "venv")
        if ($UseSystemPackages) { $venvArguments += "--system-site-packages" }
        $venvArguments += $VenvPath
        & $Python @venvArguments
        if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno Python." }
    }
    & $venvPython --version
    if ($LASTEXITCODE -ne 0) { throw "Entorno inválido. Usa otro VenvPath; no se modificó el anterior." }
    $installArguments = @("-m", "pip", "install")
    if ($Wheelhouse) { $installArguments += @("--no-index", "--find-links", $Wheelhouse) }
    & $venvPython @installArguments -r requirements.txt "setuptools>=65"
    if ($LASTEXITCODE -ne 0) { throw "Faltan dependencias: comprueba conectividad o un wheelhouse compatible." }
    & $venvPython -m pip install --no-build-isolation --no-deps -e .
    if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar el paquete local." }
    Write-Output "Listo. Ejecuta: $venvPython -m pytest -q"
    Write-Output "Aplicación: $venvPython -m streamlit run app.py"
} finally {
    Pop-Location
}
