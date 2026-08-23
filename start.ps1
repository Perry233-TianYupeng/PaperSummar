# ============================================================
# PaperSummar - one-command launcher (PowerShell 5.1 compatible)
# Python detection only; the heavy lifting is in scripts/launch.py.
# ============================================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/4] Checking Python ..."
$PYBIN = $null

if ($env:PAPERSUMMAR_PYTHON) {
    $PYBIN = $env:PAPERSUMMAR_PYTHON
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        $PYBIN = (py -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1)
    } catch { }
}
if (-not $PYBIN) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            $PYBIN = (python -c "import sys, venv; print(sys.executable)" 2>$null | Select-Object -First 1)
        } catch { }
    }
}
if (-not $PYBIN) {
    $candidates = @(
        "$env:USERPROFILE\anaconda3\python.exe",
        "$env:USERPROFILE\miniconda3\python.exe",
        "C:\ProgramData\anaconda3\python.exe",
        "C:\ProgramData\miniconda3\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $PYBIN = $c; break }
    }
}

if (-not $PYBIN) {
    Write-Host "[ERROR] No working Python found."
    Write-Host "        The 'python' in PATH may be the Microsoft Store stub."
    Write-Host "        Install Python 3.11+ from https://www.python.org/downloads/ (check Add to PATH),"
    Write-Host "        or set env var PAPERSUMMAR_PYTHON to your python.exe."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "      Using Python: $PYBIN"

Write-Host "[2/4] Running setup and launch ..."
& $PYBIN "$PSScriptRoot\scripts\launch.py"
exit $LASTEXITCODE
