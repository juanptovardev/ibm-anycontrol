# matriz-ibm-agent

Agente que, por **MCP de AnyDesk**, opera el emulador IBM 5250 de un PC de
oficina como lo haría una persona: busca la dirección en la cuenta matriz, lee
el listado de suscriptores y pega las filas en la hoja de Google Sheets.

- Runtime: Hermes (perfil `matriz-ops`) + scripts Python locales por MCP stdio.
- Transporte: `dev/mcp-anydesk` (fork propio) v3.7.0 — teclas especiales, clic
  con coordenadas, captura 1:1 del viewport.
- Lectura: Tesseract local (rápido, determinista) + Jev `jev-1.13-free` como
  segunda opinión (no ve imágenes; solo texto).

Estado actual: **E0** (humano valida cada paso). El ciclo de lectura y la macro
de búsqueda están medidos en vivo; falta el pegado en la hoja (batch T-IBM-03).

---

## Requisitos

| Pieza | Dónde | Nota |
|-------|-------|------|
| AnyDesk abierto y conectado al PC de oficina | PC del operador | La ventana `Oficina - AnyDesk` debe existir |
| Emulador IBM 5250 al frente | PC remoto | Requisito del operador (SOLO-HUMANO) |
| Chrome con `MATRICES - Google Sheets` | PC remoto | Pestaña abierta antes del ciclo |
| Python con `mss`/PIL/Tesseract | `dev/mcp-anydesk\.venv\Scripts\python.exe` | El Python global **no** sirve |
| Tesseract | `C:\Program Files\Tesseract-OCR` | 5.4.0 |
| `dev/mcp-anydesk` | repo hermano | ≥3.7.0 (necesita `click_point`, `find_viewport`) |

## Comandos

```powershell
$PY   = "C:\Users\juanp_8h8f07l\dev\mcp-anydesk\.venv\Scripts\python.exe"
$REPO = "C:\Users\juanp_8h8f07l\dev\matriz-ibm-agent"

# hwnd actual de la ventana AnyDesk (cambia por sesión)
(Get-Process anydesk | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1).MainWindowHandle

& $PY "$REPO\tools\estado.py"   <hwnd>     # ¿qué pantalla es? (JSON)
& $PY "$REPO\tools\rows.py"     <hwnd>     # medir filas del formulario (--draw)
& $PY "$REPO\tools\geo.py"      <hwnd>     # geometría + viewport
& $PY "$REPO\tools\flow.py"     <hwnd>     # macro 5250 (clic, flechas, +, F10, Shift+F4)
& $PY "$REPO\tools\paginar.py"  <hwnd> 10  # recorrer el libro con AvPág
& $PY "$REPO\tools\loop.py"     <hwnd>     # ciclo por dirección (lee datos/datos.csv)
& $PY -m unittest discover -s "$REPO\tests" -v         # 54 tests (stdlib, sin pytest)
```

## Contratos congelados

- `datos/datos.csv` — entrada:
  `id,direccion_parte1,direccion_parte2,comuna,cuenta_matriz_esperada,nota`
- `datos/ledger.csv` — salida append-only:
  `id,direccion_parte1,direccion_parte2,comuna,cuenta_matriz_esperada,estado,paginas_vistas,filas_copiadas,hora_inicio,hora_fin,evidencia,notas,reintentos`
  (la lectura toma la última fila por `id`)

## Mapa

| Ruta | Qué es |
|------|--------|
| `tools/estado.py` | Captura → OCR → reglas → (Jev) → estado de pantalla |
| `tools/tabla.py` | Parser del listado + normalización OCR por campo |
| `tools/paginar.py` | AvPág con paradas |
| `tools/loop.py` | Ciclo por dirección con blindaje B1..B7 + ledger |
| `tools/flow.py` | Macro 5250 determinista |
| `tools/rows.py` | Medición de filas por píxeles (nunca cachear coords) |
| `tools/native_shot.py` | Captura 1:1 (PrintWindow) |
| `tools/_mcp.py` | Transporte MCP (env-overridable, exit codes) |
| `tools/_jev.py` | Cliente Jev (curl, clave en archivo temporal) |
| `tools/_experimentos/` | Scripts de una vez (no tocar en producción) |
| `docs/engineering/` | Guía ORCA, batches, bitácora, TRACE_FUNCIONES |
| `docs/adr/` | Decisiones fechadas |
| `ESCALAMIENTO.md` | Blindaje, puertas E0–E3, pendientes honestos |

## Blindaje (resumen)

1. No se teclea a ciegas: la pantalla debe estar en `formulario`.
2. No se pulsa F10 sin verificar (por píxeles) que el texto quedó en Calle y no
   en Nombre.
3. Estado inesperado → el item se aborta (distinguir "no existe" de "falló").
4. El foco lo vigila el server: si una ventana local roba el foco, la llamada
   MCP falla y el item se marca error.
5. Máximo 1 reintento por item.
6. Todo item deja rastro (ledger + captura).
7. Idempotencia: lo `ok` no se reprocesa.

## Límites del emulador (medidos)

- `delete` no borra · `home` salta al primer campo · el avance de campo es el
  `+` del **bloque numérico** · `F4` suelto **cierra** el emulador (siempre con
  `shift`).
