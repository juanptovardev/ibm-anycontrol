@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\mcp-anydesk\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo ERROR: falta el venv de mcp-anydesk:
  echo        %PY%
  echo Instala primero el repositorio hermano dev\mcp-anydesk.
  pause
  exit /b 2
)
set "PERFIL=%~1"
if "%PERFIL%"=="" set "PERFIL=psicopata"

echo [1/3] visor...
start "matriz-visor" /min "%PY%" tools\ui.py
timeout /t 3 >nul

echo [2/3] datos del panel (celular en la misma red WiFi):
type datos\ui_token.txt 2>nul
echo.
ipconfig | findstr /i "IPv4"

echo [3/3] agente (perfil %PERFIL%)...
start "matriz-agente" /min cmd /c ""%PY%" -u tools\supervisor.py --perfil=%PERFIL% --teclas=rapido --max-vueltas=20 --horas=30 --tope-vuelta=21600 1> datos\auto.log 2> datos\auto.err"

echo.
echo Listo. En el celular: http://IP-de-arriba:8765/?k=TOKEN
pause
