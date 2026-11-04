@echo off
rem Executa o pipeline do podcast e grava a saida em dados\logs\agente.log.
cd /d "%~dp0"
if not exist "dados\logs" mkdir "dados\logs"
set PYTHONUTF8=1
echo ===== %date% %time% ===== >> "dados\logs\agente.log"
".venv\Scripts\python.exe" main.py >> "dados\logs\agente.log" 2>&1
echo Saida com codigo %errorlevel% >> "dados\logs\agente.log"
