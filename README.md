# IBM AnyControl (v1.0)

Agente autonomo que opera un terminal IBM 5250 remoto (via AnyDesk) para extraer
suscriptores de cuentas matriz y pegarlos en Google Sheets. Repo interno de empresa.

- Servidor MCP de control remoto: https://github.com/juanptovardev/mcp-anydesk (tag v1.1)
- Panel de control en red + token, con botones PAUSAR / DETENER / MATAR.
- Supervisor que relanza, reconecta y reanuda solo. 394 tests.

## Que hace

1. Entra al formulario CONSULTA EDIFICIO-CUENTA MATRIZ (con re-login automatico).
2. Escribe la direccion en partes (Calle / No.Casa), prellena BOG/TVC, dispara F10.
3. Lee la ficha del edificio desde el portapapeles remoto (sin OCR).
4. Entra al listado de unidades (Shift+F4) y por cada pagina:
   selecciona el bloque (7 abajo + Shift+clic), Ctrl+C, cambia a Chrome por el
   icono de la taskbar, Ctrl+Shift+V, desplaza el cursor y vuelve al 5250.
5. Avanza pagina con AvPag leyendo el contador NN/NNN, detecta fin de archivo.
6. Deja todo en el ledger (tabla, una fila por direccion, reanudable por pagina).

## Requisitos

- Windows 10/11 + Python 3.11+ con: mss, pillow, pytesseract, pywin32, opencv-python.
- Tesseract-OCR 5.x en PATH.
- AnyDesk (licencia gratuita sirve, corta cada pocos minutos: el agente reconecta solo).
- Chrome en el escritorio remoto con la hoja destino abierta (pestaña "temp borrador").
- `dev/mcp-anydesk` instalado en un venv (es el servidor MCP que el agente llama).

## Arranque

```
arranca.bat            # visor + supervisor (perfil psicopata, teclas rapidas)
arranca.bat humano     # otro perfil: sigiloso | humano | rapido | psicopata
```

Manual:

```
python tools\ui.py                                            # panel en :8765
python tools\supervisor.py --perfil=psicopata --teclas=rapido --max-vueltas=20 --horas=30 --tope-vuelta=21600
```

## Panel desde el celular

`http://<IP-de-la-PC>:8765/?k=<token>` (token en `datos/ui_token.txt`, se genera solo).
Muestra pantalla remota, semaforo por etapa, ledger y traza. FireWall de Windows:
permitir entrada TCP 8765 en perfil privado.

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
| `%USERPROFILE%\.matriz\creds.json` | `{usuario, clave}`             | login del 5250 (fuera del repo) |
| `datos/control.json`    | `{"accion": pausar\|detener\|libre}`      | runtime, lo escribe el panel |

El campo `ficha` es multilinea entre comillas y lleva `;` dentro: parsear SIEMPRE
con el modulo `csv`, nunca con split.

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
python -m unittest discover -s tests    # 394 tests, sin pytest
```

## Notas de operacion

- El hwnd de AnyDesk y del viewport rotan en cada reconexion: nunca cachearlos.
- El cambio de ventana 5250 <-> Chrome se hace por icono de taskbar (Alt+Tab no llega).
- Excel abierto bloquea direcciones.csv: las fichas van a `datos/fichas_pendientes.csv`.
- `no_encontrado` y `pegado_dudoso` son estados terminales: no se reintentan.
- Una direccion con 3 fallos consecutivos se congela y no se reintenta.
