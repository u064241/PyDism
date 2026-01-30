<#
.SYNOPSIS
    Build PyDism.exe using PyInstaller

.DESCRIPTION
    Creates a standalone executable for PyDism with all dependencies bundled.
    Includes icon, documentation, and required DLLs.

.PARAMETER Clean
    Clean build and dist folders before and after building

.EXAMPLE
    .\Build.ps1
    Basic build without cleaning

.EXAMPLE
    .\Build.ps1 -Clean
    Build with cleanup of temporary folders
#>

[CmdletBinding()]
param(
    [Parameter()]
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# Colori per l'output
function Write-Step {
    param([string]$Message)
    Write-Host "`n[BUILD] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Verifica di essere nella directory corretta
if (-not (Test-Path "PyDism.py")) {
    Write-Error "PyDism.py non trovato. Esegui lo script dalla directory del progetto."
    exit 1
}

if (-not (Test-Path "PyDism.spec")) {
    Write-Error "PyDism.spec non trovato."
    exit 1
}

# Verifica icona
if (-not (Test-Path "Ico\PyDism.ico")) {
    Write-Error "Icona Ico\PyDism.ico non trovata."
    exit 1
}

# Trova PyInstaller nell'ambiente virtuale o nel PATH
Write-Step "Verifica installazione PyInstaller..."
$pyinstallerPath = $null

# Cerca prima nell'ambiente virtuale del workspace
$venvPaths = @(
    "C:\SOURCECODE\.venv\Scripts\pyinstaller.exe",
    "..\..\.venv\Scripts\pyinstaller.exe",
    "..\.venv\Scripts\pyinstaller.exe",
    ".venv\Scripts\pyinstaller.exe"
)

foreach ($path in $venvPaths) {
    if (Test-Path $path) {
        $pyinstallerPath = Resolve-Path $path
        Write-Success "PyInstaller trovato nell'ambiente virtuale: $pyinstallerPath"
        break
    }
}

# Se non trovato nel venv, cerca nel PATH
if (-not $pyinstallerPath) {
    try {
        $cmd = Get-Command pyinstaller -ErrorAction Stop
        $pyinstallerPath = $cmd.Source
        Write-Success "PyInstaller trovato nel PATH: $pyinstallerPath"
    } catch {
        Write-Error "PyInstaller non trovato. Installalo con: pip install pyinstaller"
        exit 1
    }
}

# Pulizia pre-build
if ($Clean) {
    Write-Step "Pulizia cartelle temporanee (pre-build)..."
    
    if (Test-Path "build") {
        Remove-Item -Path "build" -Recurse -Force
        Write-Success "Cartella 'build' rimossa"
    }
    
    if (Test-Path "dist") {
        Remove-Item -Path "dist" -Recurse -Force
        Write-Success "Cartella 'dist' rimossa"
    }
    
    # Rimuovi anche file __pycache__
    Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force
    Write-Success "Cache Python pulita"
}

# Build
Write-Step "Inizio build di PyDism.exe..."
Write-Host "Questo potrebbe richiedere alcuni minuti..." -ForegroundColor Yellow

try {
    & $pyinstallerPath --clean --noconfirm PyDism.spec
    
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller ha restituito codice di errore $LASTEXITCODE"
    }
    
    Write-Success "Build completata con successo"
} catch {
    Write-Error "Errore durante il build: $_"
    exit 1
}

# Verifica output
Write-Step "Verifica output..."
$exePath = "dist\PyDism.exe"

if (Test-Path $exePath) {
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Success "Eseguibile creato: $exePath"
    Write-Host "Dimensione: $([math]::Round($exeSize, 2)) MB" -ForegroundColor White
} else {
    Write-Error "Eseguibile non trovato in $exePath"
    exit 1
}

# Pulizia post-build
if ($Clean) {
    Write-Step "Pulizia cartelle temporanee (post-build)..."
    
    if (Test-Path "build") {
        Remove-Item -Path "build" -Recurse -Force
        Write-Success "Cartella 'build' rimossa"
    }
    
    Get-ChildItem -Path . -Filter "*.spec~" | Remove-Item -Force
    Write-Success "File temporanei rimossi"
}

# Riepilogo
Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "BUILD COMPLETATO CON SUCCESSO" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "`nEseguibile:" -ForegroundColor White
Write-Host "  $exePath" -ForegroundColor Yellow
Write-Host "`nPer testare l'eseguibile:" -ForegroundColor White
Write-Host "  .\dist\PyDism.exe" -ForegroundColor Yellow
Write-Host ""
