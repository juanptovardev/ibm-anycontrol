# tools/ — piezas definitivas del sistema

Tres piezas, una por etapa. Todo lo demás está en `_experimentos/` (archivo,
no se borra: son las mediciones que justifican las recetas).

## 1. Formulario (búsqueda de la dirección)

| Archivo | Rol |
|---|---|
| `rows.py` | Mide las 8 filas del formulario por píxeles verdes sobre la captura 1:1. Nada hardcodeado. |
| `paso1.py` | UN clic en la celda 1 de Calle + `right`/`left` + escribe parte 1. Mide tinta: el texto tiene que caer en Calle, no en Nombre. |
| `paso2.py` | `+` (numpad) + parte 2 + `+` + F10 (con un reintento) + Shift+F4 → entra al listado. |

## 2. Extracción (copiar el bloque y pegarlo en la hoja)

| Archivo | Rol |
|---|---|
| `ciclo.py` | **La herramienta aprobada.** 7×Abajo → Shift+Clic última celda Suscript → Ctrl+C → Alt+Tab → Ctrl+Shift+V → Ctrl+Abajo + Abajo. |
| `click_sel.py` | Elige la celda objetivo por OCR (cabecera `Suscript`, códigos, última fila antes de la barra de teclas). Lo usa `ciclo.py`. |
| `cp.py` | Plan B (93 teclas) y dueño de las piezas reutilizables: `sel_box`, `_copiar`, `_pegar`, `_posicionar`, `texto_superior`. |
| `tabla.py` | Parser del listado (Direccion/Apto/Com/Div/Nodo/Suscript/Est) con normalización por campo. |
| `paginar.py` | AvPág con paradas: suscriptores / fin de libro / tope / estado ambiguo. |

## 3. Motor Jev (leer la pantalla y decidir)

| Archivo | Rol |
|---|---|
| `estado.py` | Captura 1:1 → Tesseract → reglas deterministas → Jev solo si hay duda. Estados: `formulario`, `cuenta_matriz`, `sin_coincidencia`, `error`, `None`. |
| `_jev.py` | Cliente Jev por curl (Bearer fuera de argv). Nunca lanza: devuelve dict con error. |
| `loop.py` | Bucle por dirección con blindaje B1..B7 y ledger append-only. Aún sin el `ciclo` nuevo integrado. |

## Infraestructura

| Archivo | Rol |
|---|---|
| `_mcp.py` | Conexión stdio al MCP, `call`, `need_hwnd`, `report` con exit codes. |
| `native_shot.py` | Captura 1:1 real con `PrintWindow(PW_RENDERFULLCONTENT)` + `GetDIBits`. |
| `preflight_auto.py` | `step` (llama una tool y aborta con `Halt`), `shot`, `changed_px`. |

## Idioma de las herramientas

- Captura 1:1 del viewport → coordenadas del clic en las mismas unidades.
- El viewport child cambia de hwnd en cada reconexión: siempre
  `window_manager.find_viewport(raiz)`, nunca cachear.
- `read_from_anydesk` (640 px) no sirve para coordenadas.
- `write_to_anydesk` recibe el argumento `command`, no `text`.

## 4. Traza y semaforo (que paso y cual es el siguiente paso)

| Archivo | Rol |
|---|---|
| `traza.py` | Trace leader + policia de transito. Cada paso deja un evento en `datos/traza.jsonl` y una fila en `datos/traza.md`. El mapa `(etapa, resultado) -> accion` decide el siguiente paso; sin regla, se detiene. |
| `pagina.py` | `volver` (Alt+Tab a IBM) y `avanza` (AvPag + clasificar). `decide` es puro: seguir / fin / abortar. |
| `vigia.py` | Detecta el dialogo de licencia de AnyDesk y pulsa `Repetir` (ventana local, boton buscado por texto). |

Detalle en `docs/engineering/TRAZA_Y_SEMAFORO.md`.