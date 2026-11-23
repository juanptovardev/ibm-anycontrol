@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -Check
if errorlevel 1 (
  echo Preflight fallo. Corrige lo anterior y vuelve a intentar.
  pause
  exit /b 2
)
set "PY=%~dp0..\mcp-anydesk\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo ERROR: falta el venv de mcp-anydesk:
  echo        %PY%
  pause
  exit /b 2
)
set "PERFIL=%~1"
if "%PERFIL%"=="" set "PERFIL=humano"
if /i "%PERFIL%"=="psicopata" (
  echo AVISO: perfil psicopata: techo teorico ~9,15 s/dir; suelo real ~12,6 s/dir.
)

echo [1/3] visor...
start "matriz-visor" /min "%PY%" tools\ui.py
timeout /t 3 >nul

echo [2/3] panel local: http://127.0.0.1:8765/
echo     token guardado en: datos\ui_token.txt
if /i "%MATRIZ_UI_BIND%"=="0.0.0.0" (
  echo     panel LAN habilitado; usa la IP local mostrada por ipconfig
  ipconfig | findstr /i "IPv4"
)

echo [3/3] agente (perfil %PERFIL%)...
start "matriz-agente" /min cmd /c ""%PY%" -u tools\supervisor.py --perfil=%PERFIL% --teclas=rapido --max-vueltas=20 --horas=30 --tope-vuelta=21600 1> datos\auto.log 2> datos\auto.err"

echo.
echo Listo. Abre http://127.0.0.1:8765/ e introduce el token de datos\ui_token.txt
pause
