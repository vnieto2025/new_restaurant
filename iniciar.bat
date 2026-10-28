@echo off
rem Levanta el backend (FastAPI) y el frontend (Vite) de RestaurantERP, cada uno en su ventana.
rem Para detenerlos, cierre las dos ventanas o presione Ctrl+C en cada una.

setlocal
set "ROOT=%~dp0"
set "PYTHON=%ROOT%backend\env\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo No se encontro el entorno virtual del backend en:
    echo   %PYTHON%
    echo Creelo con: python -m venv backend\env  e instale requirements.txt
    pause
    exit /b 1
)

where pnpm >nul 2>nul
if errorlevel 1 (
    echo No se encontro pnpm. Instalelo con: npm install -g pnpm
    pause
    exit /b 1
)

echo Iniciando backend en http://localhost:8000 ...
rem seed.py aplica las migraciones pendientes antes de arrancar
start "RestaurantERP - Backend" /D "%ROOT%backend" cmd /k ""%PYTHON%" seed.py && "%PYTHON%" main.py"

echo Iniciando frontend en http://localhost:5173 ...
start "RestaurantERP - Frontend" /D "%ROOT%frontend" cmd /k "pnpm dev --host"

rem Espera unos segundos a que los servidores arranquen y abre el navegador
timeout /t 5 /nobreak >nul
start "" http://localhost:5173

endlocal
