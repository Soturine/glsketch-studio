$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
python -m pip install -e ".[build]"
python -m PyInstaller --noconfirm --clean --windowed --name GLSketchStudio --paths src src/glsketch/__main__.py
$Archive = Join-Path $ProjectRoot "dist\GLSketchStudio-Windows-x64.zip"
if (Test-Path -LiteralPath $Archive) { Remove-Item -LiteralPath $Archive }
tar.exe -a -c -f $Archive -C (Join-Path $ProjectRoot "dist\GLSketchStudio") .
Write-Host "Artifact: $Archive"
