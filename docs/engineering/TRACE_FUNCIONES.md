# TRACE_FUNCIONES — catálogo anti-reescritura

Antes de escribir código nuevo en `tools/`: busca aquí, luego `grep` en
`dev/mcp-anydesk`. Si el repo ya resuelve ≥80%, **reutiliza**; duplicado funcional
= rechazo en auditoría. Registra la entrada nueva en el mismo commit.

Creado: 2026-10-27. Fuente: inventario real del repo (`tools/`, `tests/`).

---

## 1. Transporte MCP — `tools/_mcp.py`

| Función | Qué resuelve | Reutilízala para |
|---------|--------------|-------------------|
| `connect()` | Sesión MCP stdio con el server anydesk | Cualquier script que toque la pantalla |
| `call(s, name, args)` | Invoca una tool MCP y devuelve el dict de resultado | Todo lo que hable con el server |
| `need_hwnd(argv, pos, extra)` | Resuelve hwnd desde argv o `MCP_ANYDESK_HWND`; uso inválido → exit 2 | CLI de todas las tools |
| `report(ok, msg)` | Resultado a stdout + código de salida a stderr | Todo script con exit code |

Variables de entorno: `MCP_ANYDESK_REPO` (repo del fork), `MCP_ANYDESK_HWND`.

## 2. Captura 1:1 — `tools/native_shot.py`

| Función | Qué resuelve |
|---------|--------------|
| `print_window(hwnd)` | `PrintWindow(PW_RENDERFULLCONTENT)` + `GetDIBits` → captura 1:1 **aunque la ventana esté tapada** |
| `screen_grab(hwnd)` | Fallback con `mss` (graba la región de pantalla; inútil si la ventana está oculta) |
| `grab(hwnd)` | Devuelve la mejor imagen disponible (1:1) |
| `save(img, label)` | Guarda en `evidencia/` con timestamp |
| `client_box(hwnd)` | Rectángulo del cliente en coordenadas de pantalla |

**Por qué existe**: el screenshot de MCP está capado a 640 px (factor 1.6 sobre
1024) → las coordenadas no sirven. `native_shot` da la pantalla real 1:1.

## 3. Clasificación de pantalla — `tools/estado.py`

| Función | Qué resuelve |
|---------|--------------|
| `captura(hwnd)` | Captura 1:1 + OCR Tesseract (psm 6, x1, sin reescalar) |
| `normaliza(s)` | Limpieza de texto OCR |
| `reglas(texto)` | Reglas **puras**: `CONSULTA UNIDADES`→`cuenta_matriz`, `CONSULTA EDIFICIO`→`formulario`, avisos duros→`error`, `NO SE ENCUENTRA`→`sin_coincidencia` |
| `clasificar(texto)` | Reglas primero; si dudas → Jev; confianza Jev <0.6 → `estado=None` + error |
| `ocr_text`, `main` | CLI (`--img <png>` para clasificar una captura guardada) |

**Regla**: "DIRECCION" **no** es señal de listado (aparece en la barra
`F10=Buscar Direccion`). Señal de suscriptores = líneas con código ≥2.

## 4. Lectura del listado — `tools/tabla.py`

| Función | Qué resuelve |
|---------|--------------|
| `ocr_tabla(img)` | Recorta desde la cabecera, amplia x2 (LANCZOS) y OCR para texto pequeño |
| `_y_cabecera(img)` | Y de la fila de cabecera |
| `parse_tabla(lineas)` | Filas → dicts |
| `parse_row(linea)` | Fila → `{direccion, apto, com, div, nodo, suscript, est}` anclado a la derecha |
| `normaliza_direccion` / `normaliza_apto` / `normaliza_codigo` / `normaliza_token` | Normalización OCR **por campo** (global rompe palabras: `CL`→`C1`) |
| `extrae(...)` | Pipeline completo sobre una imagen |

**Suscriptor = penúltima columna** (antes de `Est` D/S/E). El código de Nodo
(`XT121E`, `NFE700`) se repite en todas las filas y **no** es un suscriptor.

## 5. Paginación — `tools/paginar.py`

| Función | Qué resuelve |
|---------|--------------|
| `recorre(hwnd, max, s)` | AvPág encadenado con paradas: suscriptores / fin de libro / tope / estado ambiguo |
| `hay_suscriptores(...)` | Señal de suscriptores (≥2 líneas con código) |
| `capturar_estado(...)` | Captura + clasifica en cada página |

## 6. Ciclo y blindaje — `tools/loop.py`

| Función | Qué resuelve |
|---------|--------------|
| `lee_datos()` | Lee `datos/datos.csv` (contrato congelado) |
| `ledger_leido()` / `ledger_escribe(...)` | Ledger append-only; lectura toma la última fila por `id` (idempotencia B7) |
| `espera_estado(...)` | Espera/verifica el estado esperado tras la búsqueda (B3) |
| `buscar(...)` | Ejecuta la macro 5250 |
| `verifica_texto(...)` | Verifica por **tinta de píxeles** que el texto quedó en Calle y no en Nombre (B2) |
| `procesa(...)` | Ciclo de un item con las reglas B1..B7 |

## 7. Macro 5250 — `tools/flow.py`

Secuencia congelada (una sola sesión MCP):
`focus_click off` → `pin` → detectar filas → **clic doble** en la celda 1 de Calle →
`flecha derecha` → `flecha izquierda` → escribir parte1 → `+` (numpad) →
escribir parte2 → `+` (numpad) → `F10` → `Shift+F4`.

**Límites duros del emulador (medidos, no supuestos)**
- `delete` **no borra** (el texto se acumula).
- `home` **no va al inicio del campo**: salta al primer campo del registro (Nombre).
- El avance de campo es el `+` del **bloque numérico** (`add`), no el alfanumérico.
- `F4` suelto **cierra** la ventana del emulador → siempre con `shift`.
- Tras un clic hay que "sentar" el cursor con `flecha derecha` + `flecha izquierda`.

## 8. Geometría de filas — `tools/rows.py`

`detect(hwnd)` mide por píxeles las 8 filas del formulario (Nombre, Calle,
No.Casa, Comunidad, Division, Telefono Porter, Equipo, Cuenta Edificio) y devuelve
`{y0,y1,cy,label_end,field_x}`. **Nunca caches coordenadas**: el operador
redimensiona la ventana y el formulario se desplaza.

## 9. Jev — `tools/_jev.py`

`ask(tipo, ...)` → pregunta tipada a `https://opencode.ai/inference/systemone/v1/systemone`
(modelo `jev-1.13-free`), cabecera `Bearer` en archivo temporal de curl (nunca en argv).
**Nunca lanza excepción**: devuelve `{ok:false,error}`.

Formas por tipo: `noul` → solo `instructions`; `choice` → `instructions` + `criteria`
(mapa opción→descripción); `score` → `instructions` + `criteria` como **lista
ordenada** de etiquetas (sin lista → 422 engañoso).

## 10. Tools de mcp-anydesk (v3.7.0) que este repo consume

| Tool | Uso |
|------|-----|
| `write_to_anydesk(text=<command>)` | Escribe texto. **El argumento se llama `command`, no `text`** |
| `press_keys([...])` | Teclas especiales (f10, shift+f4, add, flechas, tab, esc) |
| `click_point(x, y, button, double)` | Clic en coordenadas **del viewport** (no de la ventana) |
| `geometry(hwnd)` | Cliente, pantalla, viewport (offset + tamaño), `focus_click_enabled` |
| `set_focus_click_mode(enabled)` | Override del clic de centro (GUI flows: **desactivar**) |
| `check_health` / `initialize_session` | Foco y sesión |

---

## No duplicar

- ❌ Cliente Jev en otro repo → usar `dev/jev-gate` (MCP) o `tools/_jev.py`.
- ❌ Captura "propia" → usar `native_shot.grab/save`.
- ❌ Parser de tabla → usar `tools/tabla.py`.
- ❌ Detección de filas → usar `tools/rows.py`.
- ❌ Conexión MCP → usar `tools/_mcp.py` (con exit codes y env-overridable).
- ❌ Script de una vez → `tools/_experimentos/` (no va a `tools/`).
