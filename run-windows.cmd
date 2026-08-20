@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Primeira execucao: preparando o GLSketch Studio...
  call "%~dp0install-windows.cmd" --quiet
  if errorlevel 1 exit /b 1
)
start "GLSketch Studio" ".venv\Scripts\pythonw.exe" -m glsketch
endlocal

