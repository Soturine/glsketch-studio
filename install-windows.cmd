@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.12 ou superior nao foi encontrado.
  echo Instale pelo site https://www.python.org/downloads/windows/ marcando "Add Python to PATH".
  if /i not "%~1"=="--quiet" pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 (
  echo Nao foi possivel criar o ambiente Python 3.12.
  if /i not "%~1"=="--quiet" pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip hatchling editables
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install .
if errorlevel 1 exit /b 1
echo.
echo GLSketch Studio instalado com sucesso.
echo Use run-windows.cmd para abrir o programa.
if /i not "%~1"=="--quiet" pause
endlocal
