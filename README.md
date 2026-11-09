# IBM AnyControl v1

Agente autonomo que opera un terminal IBM 5250 remoto via AnyDesk, extrae
suscriptores de cuentas matriz y pega los resultados en Google Sheets.

**Repositorio interno privado.** Esta version contiene contratos y datos operativos
de la empresa. No hacerlo publico ni activar port-forwarding del panel.

- Agente: https://github.com/juanptovardev/ibm-anycontrol (tag v1.0)
- MCP: https://github.com/juanptovardev/mcp-anydesk (tag v1.1)
- Panel en red con token: PAUSAR / DETENER / MATAR.
- Supervisor: reconecta, reloguea, reanuda y congela fallos repetidos.
- Estado de referencia: 394 tests verdes.

## Que hace

1. Entra al formulario CONSULTA EDIFICIO-CUENTA MATRIZ (con re-login automatico).
2. Escribe la direccion en partes (Calle / No.Casa), prellena BOG/TVC, dispara F10.
3. Lee la ficha del edificio desde el portapapeles remoto (sin OCR).
4. Entra al listado de unidades (Shift+F4) y por cada pagina:
   selecciona el bloque (7 abajo + Shift+clic), Ctrl+C, cambia a Chrome por el
   icono de la taskbar, Ctrl+Shift+V, desplaza el cursor y vuelve al 5250.
5. Avanza pagina con AvPag leyendo el contador NN/NNN, detecta fin de archivo.
6. Deja todo en el ledger (tabla, una fila por direccion, reanudable por pagina).

## Instalacion en otra laptop (para la IA instaladora)

La persona de la laptop no necesita programar. Debe abrir OpenCode y pegar el
prompt de la seccion siguiente. La estructura de carpetas debe quedar asi:

```text
%USERPROFILE%\dev\mcp-anydesk
%USERPROFILE%\dev\ibm-anycontrol
```

### Requisitos

- Windows 10/11 + Python 3.11+ con: mss, pillow, pytesseract, pywin32, opencv-python.
- Tesseract-OCR 5.x en PATH.
- AnyDesk (licencia gratuita sirve, corta cada pocos minutos: el agente reconecta solo).
- Chrome en el escritorio remoto con la hoja destino abierta (pestaña "temp borrador").
- Git y acceso al repositorio privado.
- `dev/mcp-anydesk` instalado en un venv: es el servidor MCP que el agente llama.

### Prompt para OpenCode

Pegar este texto como primera instruccion en la laptop nueva:

```text
Configura IBM AnyControl v1 en esta laptop siguiendo README.md, sin inventar rutas.

1. Verifica Windows, Python 3.11+, Git y Tesseract-OCR 5.x en PATH.
2. Verifica que estos repos esten lado a lado:
   %USERPROFILE%\dev\mcp-anydesk
   %USERPROFILE%\dev\ibm-anycontrol
   Si faltan, clona los repos privados de juanptovardev usando gh auth login.
3. En mcp-anydesk crea .venv e instala el proyecto con:
   .venv\Scripts\python.exe -m pip install -e .
4. Verifica que exista:
   %USERPROFILE%\.matriz\creds.json
   con las credenciales del 5250 proporcionadas por el operador. No muestres ni
   imprimas la clave. No la guardes en el repositorio.
5. No cambies config/jev.json, datos/direcciones.csv ni datos/ledger.csv.
   Son contratos internos preparados para esta instalacion.
6. Ejecuta desde ibm-anycontrol, usando el Python del venv de mcp-anydesk:
   python -m unittest discover -s tests
   Deben pasar los tests esperados para el commit instalado.
7. Verifica que AnyDesk este abierto y conectado al PC remoto, que Chrome remoto
   tenga la hoja LIMPIEZA RR en la pestaña temp borrador y que Excel este cerrado.
8. Ejecuta primero solo el panel:
   python tools\ui.py
   Informa la IP LAN y el token. No lances el supervisor hasta que el operador
   confirme que ve el panel desde su celular.
9. Cuando el operador confirme, ejecuta arranca.bat.
10. No edites el flujo, no cambies el CSV, no resetees el ledger y no ejecutes
    una prueba nueva sin confirmacion explicita del operador.

Al terminar reporta solamente: precondiciones, tests, URL del panel, estado de
AnyDesk y si arranca.bat quedo listo.
```

### Credenciales del 5250

No estan en el repo. Crear este archivo localmente, con la clave entregada por
el operador:

```text
%USERPROFILE%\.matriz\creds.json
```

Formato:

```json
{"usuario":"USUARIO_5250","clave":"CLAVE_5250"}
```

Tambien se aceptan las variables `MATRIZ_5250_USUARIO` y
`MATRIZ_5250_CLAVE`. Nunca imprimir la clave ni pegarla en un log.

### Configuracion de Jev

`config/jev.json` ya contiene el endpoint, modelo y clave del repositorio
privado. Si la clave se rota, editarlo solo en el repositorio privado y volver a
probar; si el repositorio deja de ser privado, rotar la clave inmediatamente.

## Arranque

```text
arranca.bat            # visor + supervisor (perfil psicopata, teclas rapidas)
arranca.bat humano     # sigiloso | humano | rapido | psicopata
```

`arranca.bat` calcula la ruta del venv relativa al repositorio hermano; no
contiene una ruta de usuario fija.

Manual:

```
python tools\ui.py                                            # panel en :8765
python tools\supervisor.py --perfil=psicopata --teclas=rapido --max-vueltas=20 --horas=30 --tope-vuelta=21600
```

## Panel desde el celular

`http://<IP-de-la-PC>:8765/?k=<token>` (token en `datos/ui_token.txt`, se genera solo).
Muestra pantalla remota, semaforo por etapa, ledger y traza. FireWall de Windows:
permitir entrada TCP 8765 en perfil privado.

El telefono debe estar en la misma red WiFi. Regla de firewall, una vez como
Administrador:

```powershell
netsh advfirewall firewall add rule name="Matriz UI 8765" dir=in action=allow protocol=TCP localport=8765 profile=private
```

## Como parar

1. Panel: PAUSAR (se congela entre bloques) o DETENER (corta limpio).
2. Panel: MATAR (taskkill del arbol del agente).
3. Fisico: apagar el PC / quitar la red. El ledger reanuda sin duplicar.

## Contratos de datos (van en el repo, uso interno)

| Archivo               | Formato                                   | Uso |
| --------------------- | ----------------------------------------- | --- |
| `datos/direcciones.csv` | BOM + CRLF + `;` cabecera `parte1;parte2;ficha` | entrada, ids posicionales D01.. |
| `datos/ledger.csv`      | BOM + CRLF + `;` 13 campos, upsert por id | estado por direccion, reanudacion |
| `config/jev.json`       | `{url, model, key}`                       | clave y endpoint de Jev |
| `%USERPROFILE%\.matriz\creds.json` | `{usuario, clave}`             | login del 5250 (fuera del repo, gana sobre el de repo) |
| `config/creds.json`     | `{usuario, clave}`                       | login del 5250 (en repo, fallback portable) |
| `datos/control.json`    | `{"accion": pausar\|detener\|libre}`      | runtime, lo escribe el panel |

El campo `ficha` es multilinea entre comillas y lleva `;` dentro: parsear SIEMPRE
con el modulo `csv`, nunca con split.

## Dos entornos (mitades)

`datos/direcciones.csv` lleva la PRIMERA mitad (2168) y es la que arranca por
defecto. La SEGUNDA mitad (2167) esta en `datos/direcciones_segunda.csv`.

Para el segundo entorno (otra laptop), antes de `arranca.bat`:

```powershell
copy datos\direcciones_segunda.csv datos\direcciones.csv
python tools\reset_ledger.py
```

Ambos entornos corren su mitad sin solaparse (cada uno con su propio ledger).

## Estructura de tools/

- Orquestacion: `loop.py`, `orquesta.py`, `autonomo.py`, `supervisor.py`
- Flujo: `matriz_buscar.py`, `matriz_ficha.py`, `matriz_extraer.py`, `pagina.py`
- E/S remota: `cp.py`, `ciclo.py`, `click_sel.py`, `ventana.py`, `estado.py`,
  `preflight_auto.py`, `enfocar.py`, `native_shot.py`, `_mcp.py`, `_jev.py`
- Resiliencia: `vigia.py`, `login.py`, `credenciales.py`, `traza.py`, `perfil.py`
- Datos: `separar.py`, `anexar_direcciones.py`, `regenerar_direcciones.py`,
  `reset_ledger.py`, `registrar_pegado.py`
- Panel: `ui.py` + `arranca.bat`

## Perfiles de velocidad

| Perfil    | Techo s/direccion | Nota |
| --------- | ----------------- | ---- |
| sigiloso  | 27,5              | 1,5x mas lento que el operador humano |
| humano    | 18,3              | ritmo de referencia |
| rapido    | 12,2              | |
| psicopata | 9,15              | corre al maximo real del motor |

El techo se rellena con pausas naturales (4 puntos, con jitter). Si el motor va
mas lento que el techo no se anade pausa.

## Tests

```
python -m unittest discover -s tests    # 394 tests de referencia, sin pytest
```

## Notas de operacion

- El hwnd de AnyDesk y del viewport rotan en cada reconexion: nunca cachearlos.
- El cambio de ventana 5250 <-> Chrome se hace por icono de taskbar (Alt+Tab no llega).
- Excel abierto bloquea direcciones.csv: las fichas van a `datos/fichas_pendientes.csv`.
- `no_encontrado` y `pegado_dudoso` son estados terminales: no se reintentan.
- Una direccion con 3 fallos consecutivos se congela y no se reintenta.
- El agente controla el cursor y el foco de la laptop. No usar esa laptop mientras
  corre; detener desde el panel del celular. Manana conviene moverlo a un PC
  dedicado.
