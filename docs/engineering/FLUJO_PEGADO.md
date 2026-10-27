# Flujo de copiado y pegado (bloque congelado del operador)

Segunda mitad del ciclo: ya se buscó la dirección y estamos en
`CONSULTA UNIDADES CUENTA MATRIZ`. Ahora se copia el bloque de suscriptores y
se pega en la hoja de limpieza.

## Receta congelada (no reinterpretar)

| # | Acción | Detalle |
|---|---|---|
| 1 | 7 × `Abajo` **sin** Shift | mueve el cursor al primer renglón de datos |
| 2 | `Shift` mantenido | la barra del cursor pasa a ser selector |
| 3 | 72 × `Derecha` | cubre horizontal de `Direccion` a `Suscript` |
| 4 | 14 × `Abajo` | 15 filas en total |
| 5 | soltar `Shift` | la selección queda fija |
| 6 | `Ctrl+C` | copia al portapapeles remoto |
| 7 | `Alt+Tab` | pasa a la hoja de limpieza |
| 8 | `Ctrl+Shift+V` | pega sin formato |
| 9 | `Ctrl+Shift+Abajo` | selecciona hasta el final de la columna |
| 10 | 1 × `Abajo` | deja la celda lista para el siguiente pegado |

Todo va en **una sola sesión MCP** (pin + override de foco son por proceso).

## Implementación

`tools/cp.py`:

```
python tools/cp.py <hwnd> --dry   # solo selecciona y mide. NO copia.
python tools/cp.py <hwnd>         # copia y pega una vez
```

Constantes del bloque (congeladas, con test que falla si cambian sin querer):
`BAJAR_INICIO = 7`, `ANCHO = 72`, `ALTO = 14`, `KEY_DELAY_MS = 45`
(93 teclas → ~8 s; más rápido empieza a perder pulsaciones).

## Puertas

| Puerta | Qué verifica | Si falla |
|---|---|---|
| G0 | la pantalla es el listado (`estado == cuenta_matriz`) | aborta, no teclea |
| G1 | la selección es un rectángulo macizo (`densidad ≥ 0.30`) y de tamaño plausible | aborta antes de Ctrl+C |
| G2 | tras `Alt+Tab` la pantalla **no** es IBM | aborta, no pega |
| G3 | tras `Ctrl+Shift+V` hubo cambio visible (`≥ 3000 px`) | un reintento y aborta |

G1 imprime además el OCR de la primera línea de la selección: si ahí aparece
la cabecera (`Direccion Apto…`), el bloque empezó una fila arriba y hay que
corregir `BAJAR_INICIO`.

## Por qué no se puede verificar el portapapeles

El portapapeles vive en la máquina remota. Este proceso nunca lo lee: la
única prueba de que `Ctrl+C` funcionó es que el pegado produzca un cambio
visible en la hoja (G3).

Si G3 falla dos veces, la conclusión honesta es **"AnyDesk no reenvía
Ctrl+C programático"**. Alternativa entonces: leer el bloque con OCR
(`tabla.extrae`, ya funciona) y escribir celda por celda con
`write_to_anydesk` + `Tab`. Más lento (~2-3 min por bloque), sin
portapapeles, pero sin depender de esa tecla.

## Orden de arranque del ciclo completo

```
1. entorno      get_system_status -> anydesk_windows no vacío
2. pin          select_anydesk_window + set_focus_click_mode(false)
3. pantalla     estado.py  -> debe decir "formulario"
4. busqueda     paso1.py + paso2.py  -> debe terminar en "cuenta_matriz"
5. copiar       cp.py --dry  -> medir G1 (una vez, para fijar umbrales)
6. copiar/pegar cp.py        -> G2 + G3
```

Cada paso es un comando con salida verificable: si uno no cuadra, el
siguiente no se ejecuta.

## Plan A: Shift+Clic (menos pulsaciones, mismo resultado)

La receta de arriba gasta 93 pulsaciones (~8 s). El operador propuso
sustituir la selección por un gesto de ratón:

```text
7xAbajo -> Shift abajo -> CLIC en la ultima celda (ultima fila, columna Suscript)
        -> Shift arriba -> Ctrl+C -> Alt+Tab -> Ctrl+Shift+V -> Ctrl+Shift+Abajo -> Abajo
```

El emulador extiende la selección desde el cursor hasta la celda clicada, así
que el bloque sale idéntico al del plan B con 1 lote de teclas y 1 clic.

Implementación: `tools/click_sel.py` (reutiliza copiar/pegar/posicionar de
`cp.py`). Las coordenadas no están hardcodeadas: se miden con OCR sobre la
captura 1:1 (`target_celda`: cabecera `Suscript` + borde derecho de los códigos
de suscriptor + última fila con texto) y después se valida con `sel_box`.

Prerrequisito en el servidor: `click_point(..., shift=True)` (v3.7.3), que baja
Shift, hace el clic y suelta Shift en `finally` aunque el clic falle.

Puertas: A1 (objetivo encontrado by OCR) y A2 (el clic cae DENTRO del
rectángulo amarillo, ancho ≥ 500 px, alto ≥ 150 px). Luego G2 y G3 de `cp.py`.

## Estado

- Plan B (`cp.py`): **ejecutado en vivo con éxito** el 2026-10-27 — 15 filas
  pegadas en la hoja `LIMPIEZA RR`, suscriptores alineados en la columna J.
- Plan A (`click_sel.py`): escrito y con tests. **No ejecutado en vivo.**
- Tests del repo: 69 (`python -m unittest discover -s tests`).
