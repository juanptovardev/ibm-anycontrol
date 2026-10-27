# Flujo de copiado y pegado (bloque congelado del operador)

Segunda mitad del ciclo: ya se buscó la dirección y estamos en
`CONSULTA UNIDADES CUENTA MATRIZ`. Ahora se copia el bloque de suscriptores y
se pega en la hoja de limpieza.

## Receta congelada (no reinterpretar)

| # | Acción | Detalle |
|---|---|---|
| 1 | `Shift` mantenido | la barra del cursor pasa a ser selector |
| 2 | 7 × `Abajo` | baja al primer renglón de datos |
| 3 | 72 × `Derecha` | cubre horizontal de `Direccion` a `Suscript` |
| 4 | 14 × `Abajo` | 15 filas en total |
| 5 | soltar `Shift` | la selección queda fija |
| 6 | `Ctrl+C` | copia al portapapeles remoto |
| 7 | `Alt+Tab` | pasa a la hoja de limpieza |
| 8 | `Ctrl+V` | pega |
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
| G3 | tras `Ctrl+V` hubo cambio visible (`≥ 3000 px`) | un reintento y aborta |

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

## Estado

- Código: escrito y con tests (61 en el repo). **No ejecutado en vivo.**
- Pendiente de validar con el operador: `cp.py --dry` (medir la selección),
  y después la corrida real de copiar/pegar.
