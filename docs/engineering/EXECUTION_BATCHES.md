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
python -m unittest discover -s tests -p "test_window_manager_click.py"  -> 12/12
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
python -m unittest discover -s tests   -> todas verdes
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

## T-IBM-03 — pegado en Chrome (CERRADO)

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
python -m unittest discover -s tests                    -> todas verdes
python tools/pegar.py --columnas <mapa> --dry-run -> imprime plan, escribe 0
python tools/pegar.py --columnas <mapa>           -> ledger con filas_copiadas = N
```

**Verificación post-pegado**: captura 1:1 de la hoja → OCR → los valores pegados
deben coincidir con las filas del listado (G2: similitud ≥0.90).

---

**Resultado (CERRADO)**: la mecánica definitiva no fue "escribir celda a
celda" sino **seleccionar con Shift+Clic + portapapeles**:
`7 abajo → Shift+Clic en la última celda de Suscript → Ctrl+C → Alt+Tab →
Ctrl+Shift+V → Ctrl+Abajo → Abajo`. Herramientas: `tools/click_sel.py`
(dónde está la celda), `tools/cp.py` (copiar/pegar/posicionar),
`tools/ciclo.py` (el bloque completo). Run del piloto: **150 filas pegadas en
10 páginas** en 2 m 51 s, con `fin_libro` detectado solo. Se descartó la
premisa de "no usar Ctrl+V": se añadió la tool `paste_clipboard` (Ctrl+V y
Ctrl+Shift+V) en `mcp-anydesk` v3.7.2 sin relajar la regla de `press_keys`.

---

## T-IBM-04 — versión definitiva: página vacía, velocidad y retorno (CERRADO)

**Objetivo**: que el agente no pegue páginas en blanco, vaya más rápido y
vuelva al formulario desde el listado sin intervención.

**Alcance permitido**: `dev/matriz-ibm-agent` → `tools/`, `tests/`,
`ESCALAMIENTO.md`; `dev/mcp-anydesk` → `mcp_anydesk_server/`, `tests/`.

**Criterios de aceptación ejecutables**
```
python -m unittest discover -s tests   -> 105/105
python tools/estado.py <hwnd>           -> estado determinista, sin llamar a Jev
```

**Resultado**:
- **Página vacía = no se pega** (B8). Medido sobre 34 capturas reales: la
  vacía da 0 códigos y 0 px de tinta; las que tienen datos dan ≥1 código y
  ≥237 px. Con tinta pero sin códigos legibles se pregunta a Jev y solo se
  salta con conf ≥ 0.6 (fail-safe: nunca se pierde información).
- **Velocidad**: un OCR por captura (`ocr_completo`), captura de página
  reutilizada, `clasificar_rapido` (0,6 s), `changed_px` vectorizado, foco al
  50 ms si la ventana ya está delante. De ~20 s/página a ~6–8 s.
- **Retorno**: `Escape` + `F12` + `F12` (en `CONSULTA UNIDADES` la única tecla
  de la barra es `F12=Anterior`, y con el teclado inhibido `F3` no sale).
- **Cortes de AnyDesk**: dos causas distintas, detectadas por regla y sin
  gastar Jev (licencia vs remoto apagado).

**Commits**: `80a7c52` (agente), `2872044` (mcp-anydesk v3.7.4).

---

## T-IBM-05 — corrida en vivo de la versión definitiva (PENDIENTE) ← siguiente

**Objetivo**: probar en el PC remoto el ciclo completo con las 5 direcciones de
`datos/direcciones.csv` y medir el tiempo real por página.

**Precondiciones**
1. AnyDesk abierto en el PC remoto y **AnyDesk del cliente** sin corte de
   licencia (la licencia gratuita corta a los ~10 min: es el mayor freno).
2. Emulador 5250 en el menú principal (el agente entra solo con
   `1+ENTER+ESC+1+ENTER+1+ENTER`).
3. Chrome con la pestaña de la hoja (`LIMPIEZA RR`) abierta en el remoto.
4. `datos/direcciones.csv` con las direcciones reales.

**Prohibiciones**
- No tocar la pantalla del PC remoto mientras corre (rompe el foco; el guard
  del server lo detecta y aborta, pero se pierde el item).
- No arrancar dos `loop.py` a la vez: se pelean por la ventana.

**Criterios de aceptación ejecutables**
```
python tools/loop.py <hwnd> --dry   -> busca, clasifica, NO pega, ledger intacto
python tools/loop.py <hwnd>         -> ledger con 5 filas de estado conocido
datos/ledger.csv                     -> estado=ok, paginas_vistas y filas_copiadas > 0
tools/traza.py --json                -> cadena de etapas completa, sin 'detener'
```

**Medición a entregar**: segundos por página y por dirección, páginas
vacias saltadas, filas pegadas en la hoja, y cualquier ítem en `error` con su
motivo exacto.

---

## C-01 — cierre ciego de la etapa (PENDIENTE)

Sesión fresca, modelo distinto al del obrero. Salida:
`tools/verifications/cierre-etapa-N.md` con veredicto
**CERRADA / CERRADA-CON-RESERVAS / RECHAZADA** + escalados + SHAs.
