@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python nao encontrado. Siga primeiro a instalacao no README.md.
    pause
    exit /b 1
)
echo Restaurante Manager - mantenha esta janela aberta.
echo Abra http://127.0.0.1:5000 no computador servidor.
".venv\Scripts\python.exe" run.py
pause
