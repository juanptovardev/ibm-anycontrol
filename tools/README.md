# tools/ — piezas definitivas del sistema

Tres piezas, una por etapa. Las mediciones que justifican las recetas viven en
`docs/adr/` y `docs/engineering/`.

## 1. Formulario (búsqueda de la dirección)

| Archivo | Rol |
|---|---|
| `rows.py` | Mide las 8 filas del formulario por píxeles verdes sobre la captura 1:1. Nada hardcodeado. |
| `paso1.py` | UN clic en la celda 1 de Calle + `right`/`left` + escribe parte 1. Mide tinta: el texto tiene que caer en Calle, no en Nombre. |
| `paso2.py` | `+` (numpad) + parte 2 + `+` + F10 (con un reintento) + Shift+F4 → entra al listado. |

## 2. Extracción (copiar el bloque y pegarlo en la hoja)

| Archivo | Rol |
|---|---|
| `ciclo.py` | **La herramienta aprobada.** 7×Abajo → Shift+Clic última celda Suscript → Ctrl+C → cambio a la hoja → Ctrl+Shift+V → Ctrl+Abajo + Abajo. |
| `click_sel.py` | Elige la celda objetivo por OCR (cabecera `Suscript`, códigos, última fila antes de la barra de teclas). Lo usa `ciclo.py`. |
| `cp.py` | Plan B (93 teclas) y dueño de las piezas reutilizables: `sel_box`, `_copiar`, `_pegar`, `_posicionar`, `texto_superior`. |
| `tabla.py` | Parser del listado (Direccion/Apto/Com/Div/Nodo/Suscript/Est) con normalización por campo. |
| `paginar.py` | AvPág con paradas: suscriptores / fin de libro / tope / estado ambiguo. |

## 3. Motor Jev (leer la pantalla y decidir)

| Archivo | Rol |
|---|---|
| `estado.py` | Captura 1:1 → Tesseract → reglas deterministas → Jev solo si hay duda. Estados: `formulario`, `cuenta_matriz`, `sin_coincidencia`, `error`, `None`. |
| `_jev.py` | Cliente Jev por curl (Bearer fuera de argv). Nunca lanza: devuelve dict con error. |
| `loop.py` | Bucle por dirección con blindaje B1..B7 y ledger con upsert por id. Integra `click_sel` y `cp`. |

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
| `pagina.py` | `volver` (icono de la taskbar a IBM) y `avanza` (AvPag + clasificar). `decide` es puro: seguir / fin / abortar. |
| `vigia.py` | Detecta el dialogo de licencia de AnyDesk y pulsa `Repetir` (ventana local, boton buscado por texto). |

Detalle en `docs/engineering/TRAZA_Y_SEMAFORO.md`.

## 5. Ciclo definitivo (aprobado en vivo por el operador)

```
datos/direcciones.csv          ->  parte1;parte2;ficha   (separador ; de Excel)
        |
        v
loop.procesa  -- B0 reconectar --> B1 estado=formulario --> B2 texto en Calle
        |                                                          |
        |  F10 --> ficha del edificio --> Shift+F4 --> CONSULTA UNIDADES
        v
ciclo.extrae  ->  7 abajo (solo el 1er bloque)  ->  Shift+Clic en la celda
                  de Suscript  ->  Ctrl+C  ->  cambio a la hoja  ->  Ctrl+Shift+V
                  ->  Ctrl+Abajo  ->  Abajo
        |
        +-- pagina_vacia?  --> AvPag y seguir   (nunca se pega en blanco)
        |
        v
pagina.volver (icono de la taskbar a IBM) --> pagina.avanza (AvPag) --> pagina.decide
        |
        v
volver_formulario  ->  Escape + F12 + F12  ->  siguiente direccion
```

| Archivo | Rol |
|---|---|
| `ciclo.py` | Un bloque de extracción completo. Devuelve `"ok"` o `"vacia"`. |
| `click_sel.py` | `target_celda` (dónde está la celda) + `pagina_vacia` (¿hay suscriptores?). |
| `cp.py` | `copy_clipboard`, `paste_clipboard(shift=True)`, posicionar, `sel_box`. |
| `arranque.py` | Arranque en frío desde el menú principal. |
| `login.py` | Login del 5250 pegando usuario+clave desde el portapapeles local. |

**Coordenadas**: nunca cacheadas. `rows.detect` mide las filas del formulario y
`click_sel.target_celda` mide la celda en cada captura. El `+` del **bloque
numérico** (`press_keys ["add"]`) es el avance de campo: el `+` alfanumérico no
sirve. `delete` no borra y `home` salta al primer campo: para vaciar un campo
se sobrescribe con espacios desde la posición 0 del campo.

**Perfiles de velocidad**: `tools/perfil.py` (sigiloso / humano / rapido /
psicopata). El techo se cumple rellenando pausas naturales, nunca acelerando
por debajo. `--perfil=X` y `--teclas=rapido|humano`. Detalle y medidas en
`docs/PERFILES_VELOCIDAD.md`.