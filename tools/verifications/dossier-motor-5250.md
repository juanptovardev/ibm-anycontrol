# Dossier — motor 5250 (batches A-02, T-IBM-01, T-IBM-02)

- Fecha: 2026-10-27
- Alcance: `dev/matriz-ibm-agent` (motor) + `dev/mcp-anydesk` v3.7.0 (primitivos)
- Commits: `141b3b1`, `3cd81a8` (anydesk) · `5923c46`, `71adb59`, `b57815f`, `007b7d4` (motor)

Todo lo de abajo es **medido**, no supuesto. Cada cifra tiene el comando que la
produce.

---

## 1. Suite

```
python -m unittest discover -s tests   -> Ran 54 tests ... OK
```
Ficheros: `test_reglas.py` (clases de reglas + precedencia + `lineas_suscriptor`),
`test_tabla.py` (parser + normalización por campo), `test_paginar.py` (7 casos
mockeados), `test_jev.py` (5 casos de `_jev.ask`), `test_loop.py` (ledger/datos),
`test_mcp_helper.py` (helper MCP con sesión falsa).

```
python test_mcp_smoke.py       -> SMOKE OK, 22 tools, v3.7.0, tesseract 5.4.0
```

## 2. Captura 1:1 (prerrequisito de todo)

`tools/native_shot.py` usa `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` +
`GetDIBits` → imagen exacta **aunque la ventana esté tapada**. El fallback con
`mss` captura la región de pantalla y devolvió la terminal local del operador
(la ventana estaba oculta) → por eso `mss` es fallback, no método principal.

El screenshot de MCP está capado a 640 px (1024→640, factor 1.6): **no sirve
para coordenadas**.

## 3. Geometría del viewport

```
python tools/geo.py 198526
```
- root `198526` «Oficina - AnyDesk», cliente 1257x768 en pantalla (59,0)
- viewport child `gui.tabbar_panel`: offset (1,104), tamaño 1255x663
- el cliente de la raíz **incluye** la barra de AnyDesk (~104 px): el root no
  es la pantalla remota.

```
click_point(x=551, y=185) -> screen {x:611, y:289}
GetCursorPos()             -> (611, 289)   = (60+551, 104+185)
```
El mapeo local del clic es **exacto**.

El hwnd del root y el del viewport child **cambian por sesión**
(393712→3146792→5702798→6162232→1966118→67230; root 198526→132724).
Regla: resolver siempre con `window_manager.find_viewport(root)`.

## 4. Root cause del foco (A-02)

`config.FOCUS_CLICK_ENABLED=True` + `focus_and_verify()` llamaba
`_click_window_center(hwnd)` en **cada** foco → cada escritura movía el cursor
remoto al centro de la ventana antes de escribir. Eso explicaba "El campo
requiere caracteres numericos", el "área protegida" y que el texto cayera en
Nombre.

Fix: `set_focus_click_mode(False)` (override por sesión) + `click_point` con
coordenadas del viewport. Tests: `tests/test_window_manager_click.py` 12/12
(fuera de límites, botón inválido, mapeo, doble clic, botón derecho, override,
geometry, viewport).

## 5. Detección de filas (`tools/rows.py`)

`detect(hwnd)` mide por píxeles las 8 filas del formulario (verde `g>140, r<130,
b<130` en x=150..500, bandas de 5–26 px, se descarta lo que está sobre el mayor
hueco vertical):

| Índice | Campo | cy medido |
|--------|-------|-----------|
| 0 | Nombre | 166 |
| 1 | Calle | 185 |
| 2 | No.Casa | 204 |
| 3 | Comunidad | 223 |
| 4 | Division | 242 |
| 5 | Telefono Porter | 280 |
| 6 | Equipo | 301 |
| 7 | Cuenta Edificio | 319 |

`field_x = 531`, `label_end = 487`. El CLI `--draw` superpone las líneas
detectadas y caen sobre cada etiqueta.

**Por qué se re-mide siempre**: el operador maximiza/restaura la ventana y el
formulario se desplaza; las coordenadas cacheadas caen una fila arriba.

## 6. Límites del emulador (medidos)

| Tecla | Resultado medido |
|-------|-------------------|
| `delete` | **no borra**: `175-` → `175-175-7` |
| `home` | salta al **primer campo del registro** (Nombre) |
| `+` numérico (`add`) | avanza de campo (Calle→No.Casa→Comunidad) |
| `F4` suelto | **cierra** el emulador → bloqueado en código |
| clic + `right` + `left` | "sienta" el cursor (truco validado por el operador) |

## 7. OCR

Medición sobre captura real del 5250:

| Preprocesado | Tokens correctos |
|--------------|------------------|
| **gris x1, psm 6** | **10/10** |
| x2 LANCZOS | 9/10 |
| x3 LANCZOS | 8/10 |
| binarizada | 7/10 |
| invertida | 9/10 |

Para la **tabla** (texto minúsculo) sí hay que recortar desde la cabecera y
ampliar x2 (`tabla.ocr_tabla`).

Layout real del listado (captura real):
```
Direccion | Apto | Com | Div | Nodo | Suscript | Est
CL 175 BLACACIAS 178-10 CASA3 BOG TVC XT121E 50867551 S$
```
- **Suscript = penúltima columna** (antes de `Est` D/S/E).
- El código de Nodo (`XT121E`, `NFE700`) se repite en todas las filas y **no**
  es un suscriptor.
- Normalización OCR **por campo**: global rompe palabras (`CL`→`C1`,
  `BLACACIAS`→`BLACACIA5`). Solo se tocan tokens con dígitos; en `Apto` se parte
  por prefijo conocido (CASA/ADMIN/DEP/LOC/DPTO/PISO) y se mapea el sufijo
  (CASAL→CASA1, CASAIO→CASA10, ADMINi→ADMIN1).

## 8. Reglas de estado

| Señal en el texto | Estado |
|-------------------|--------|
| `CONSULTA UNIDADES` | `cuenta_matriz` |
| `CONSULTA EDIFICIO` | `formulario` |
| `AREA PROTEGIDA` / `REQUIERE CARACTERES` / `CODIGO COMUNIDAD` / `NO PERMITIDA` | `error` (gana sobre "no encontrado") |
| `NO SE ENCUENTRA` / `NO ESTA EN EL ARCHIVO` + formulario | `sin_coincidencia` |
| ninguna regla casa | → Jev; si confianza <0.6 → `estado=None` + error |

**"DIRECCION" no es señal de listado**: aparece en la barra `F10=Buscar Direccion`
→ falso positivo. Suscriptores = **líneas con código ≥2** (conteo de líneas).

## 9. Blindaje verificado EN VIVO

Pantalla remota = portal web ("Noticias / Este puesto de trabajo"): ninguna
regla casó. Sin umbral, B1 habría tecleado en el navegador. Con el umbral:

```
python tools/estado.py 132724
-> estado=null | fuente=jev | conf=0.4 | error="jev con confianza baja (0.4)"
   senales={"form":false,"unidades":false,"lineas":13,"lineas_suscriptor":0}
```

**No se tecleó nada.** Re-verificado en otra sesión (conf 0.32).

## 10. Jev

- Endpoint `https://opencode.ai/inference/systemone/v1/systemone`, `Bearer` en
  archivo temporal de `curl` (fuera del argv).
- Llave viva: `%LOCALAPPDATA%\opencode\auth.json` (providers `opencode` /
  `opencode-go`, misma clave `oc_sk_…`).
- `jev-1.13-free` → 200, `cost 0`. `jev-1.13` (pago) → **403 "Model access is
  disabled"** en esta cuenta.
- Formas: `noul` → solo `instructions`; `choice` → `instructions` + `criteria`
  (mapa); `score` → `instructions` + `criteria` como **lista ordenada**.
- Cuota free → 429 frecuente: por eso Jev es segunda opinión (ADR-0002/0006).

## 11. Reservas

1. **Pegar en Chrome** no existe todavía (batch T-IBM-03): falta contrato de
   columnas confirmado por el operador y verificación post-pegado.
2. **OCR de la columna SUSCRIPTOR a 1:1** sin calibrar: la captura chica garblea
   dígitos (`soBs7ss1` por `50867551`).
3. **`shift+f4` vs `f16`** para entrar al listado: sin verificar (el clasificador
   ya distingue `cuenta_matriz` de `formulario`, así que la prueba es de un clic).
4. **T0 (teclas especiales)** quedó como *aceptado por el operador*, no medido:
   la confirmación empírica se hace en el primer ciclo real.
5. `Ctrl+C` no viaja por AnyDesk → el freno real es cerrar la sesión o matar el
   proceso Python.

## 12. Veredicto

**CERRADA-CON-RESERVAS.** El motor de lectura/clasificación está verificado en
vivo y con 54 tests; el flujo de escritura está medido en el emulador; el pegado
en la hoja y la calibración fina del OCR de suscriptores quedan para el batch
siguiente.
