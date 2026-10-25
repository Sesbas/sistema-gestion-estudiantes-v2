@echo off
cd /d "%~dp0"
title Flask - Gestion de Estudiantes
echo Abre http://127.0.0.1:5000/ y deja esta ventana abierta.
".venv\Scripts\python.exe" -m flask --app backend/app.py run
pause
