# EXECUTION_BATCHES — prompts congelados

Registro de los batches ejecutados y de los pendientes. Los prompts **congelados**
no se editan: las erratas van en el launcher o en una nota de retome.
Creado: 2026-10-27.

---

## A-01 — `press_keys` en mcp-anydesk (CERRADO)

**Objetivo**: habilitar teclas especiales (F10, Shift+F4, Tab, flechas, `+` del
bloque numérico) vía MCP, sin reintroducir combinaciones vk+scan-code.

**Alcance permitido**: `dev/mcp-anydesk` → `keyboard_injector.py`, `server.py`,
`__init__.py`, `pyproject.toml`, `tests/`, `docs/`.

**Prohibiciones**: no tocar `screen_reader.py`; no reintroducir `VK`+scan code; no
inyectar `\n` ni Enter; `Ctrl+C` prohibido en código (AnyDesk lo renderiza como texto).

**Criterios de aceptación ejecutables**
```
python -m unittest discover -s tests            -> Ran 54 tests ... OK
python test_mcp_smoke.py              -> SMOKE OK, 19 tools
```

**Resultado**: `bed0e93` + `007b7d4`-style review. 30 teclas, modificadores
liberados en `finally`, foco verificado, auditado. Changelog `007`.

---

## A-02 — primitivos de ratón + raíz del foco (CERRADO)

**Objetivo**: (1) entender por qué las escrituras caían en el campo equivocado;
(2) exponer geometría y clic con coordenadas correctas.

**Alcance permitido**: `dev/mcp-anydesk` → `window_manager.py`, `win32_input.py`,
`server.py`, `__init__.py`, `pyproject.toml`, `tests/`.

**Prohibiciones**: no modificar `screenshot.py`; no capturar la pantalla
completa (solo el viewport del hijo); no tocar la sesión remota sin aprobación.

**Criterios de aceptación ejecutables**
```
python -m pytest tests/test_window_manager_click.py -q   -> 12/12
python test_mcp_smoke.py                                   -> SMOKE OK, 22 tools
```

**Resultado**: commits `141b3b1` + `3cd81a8` (v3.7.0). Root cause: `focus_and_verify`
hacía clic en el CENTRO de la ventana en cada foco (`FOCUS_CLICK_ENABLED=True`),
moviendo el cursor remoto al centro antes de escribir. Se añadió override
`set_focus_click_mode`, `geometry`, `click_point` y `find_viewport` (el root client
incluye la barra de AnyDesk: el viewport real es el hijo `gui.tabbar_panel`).

---

## T-IBM-01 — motor 5250 (CERRADO)

**Objetivo**: leer la pantalla del emulador IBM 5250 y clasificar el estado con
reglas deterministas; Jev solo como desempate.

**Alcance permitido**: `dev/matriz-ibm-agent` → `tools/`, `tests/`, `ESCALAMIENTO.md`,
`datos/`.

**Criterios de aceptación ejecutables**
```
python -m pytest tests -q        -> 54/54
python tools/estado.py <hwnd>    -> JSON con estado/fuente/confianza
```

**Resultado**: commits `b57815f` + `007b7d4`. 5 módulos (`estado`, `tabla`,
`paginar`, `loop`, `_jev`) + 54 tests.

---

## T-IBM-02 — revisión y blindaje (CERRADO)

**Objetivo**: code review adversarial del motor + cierre de los huecos que
permitían teclear en la pantalla equivocada.

**Criterios**: 6 findings aplicadas (umbral de suscriptores, `estado=None`
distinto de "error de pantalla", exit codes de CLI, confianza con `or 0.0`,
`int()` protegido, docstrings de coste).

**Resultado**: commit `007b7d4`. Blindaje verificado EN VIVO: pantalla remota =
portal web → `estado=None`, confianza 0.32, abort sin teclear.

---

## T-IBM-03 — pegado en Chrome (PENDIENTE) ← siguiente

**Objetivo**: cerrar el ciclo completo: leer el listado, pegar las filas en la
hoja de Google Sheets y verificar el pegado.

**Alcance permitido**: `dev/matriz-ibm-agent` → `tools/pegar.py`, `tools/chrome.py`,
`tests/`, `ESCALAMIENTO.md`.

**Precondiciones**
1. `dev/mcp-anydesk` en ≥3.7.0 (necesita `click_point` + `find_viewport`).
2. Emulador 5250 al frente en el PC remoto (lo trae el operador).
3. Chrome con la pestaña `MATRICES - Google Sheets` abierta en el PC remoto.
4. **Contrato de columnas confirmado por el operador** (nº de columna por campo:
   id, dirección, edificio, suscriptor). Sin ese dato NO se pega: se pregunta.

**Prohibiciones**
- No usar `Ctrl+V` (no viaja por AnyDesk): el pegado es **escritura carácter a
  carácter** con `write_to_anydesk`.
- No copiar/pegar el portapapeles de la máquina local.
- No teclear en Chrome sin haber verificado por captura que la ventana activa es
  la hoja (el mismo bug de foco que rompió el 5250).
- No borrar ni sobrescribir celdas existentes: solo escribir en celdas vacías
  debajo de la última fila con datos.

**Criterios de aceptación ejecutables**
```
python -m pytest tests -q                        -> todas verdes
python tools/pegar.py --columnas <mapa> --dry-run -> imprime plan, escribe 0
python tools/pegar.py --columnas <mapa>           -> ledger con filas_copiadas = N
```

**Verificación post-pegado**: captura 1:1 de la hoja → OCR → los valores pegados
deben coincidir con las filas del listado (G2: similitud ≥0.90).

---

## C-01 — cierre ciego de la etapa (PENDIENTE)

Sesión fresca, modelo distinto al del obrero. Salida:
`tools/verifications/cierre-etapa-N.md` con veredicto
**CERRADA / CERRADA-CON-RESERVAS / RECHAZADA** + escalados + SHAs.
