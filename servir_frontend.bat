@echo off
rem Abre a landing page em http://localhost:8000 (Ctrl+C para parar).
cd /d "%~dp0"
start "" "http://localhost:8000"
".venv\Scripts\python.exe" -m http.server 8000 --directory frontend
