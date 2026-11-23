# Modularización del agente — plan propuesto (sin ejecutar)

Estado actual: `loop.py` tiene ~900 líneas y mezcla cinco responsabilidades.
Funciona (D01, D02, D03 completas: 35 páginas, 525 filas, 4/5 fichas), así que
la regla de la refactorización es: **mismo comportamiento observable, mismos
tests, mismos contratos**. Si algo cambia de resultado, se revierte.

## Objetivo

Un archivo = una responsabilidad = una decisión.
El orquestador **solo secuencia**: nunca teclea, nunca hace clic, nunca mira píxeles.

```
tools/
  enfocar.py                # (existe) foco del escritorio remoto
  contexto.py               # NUEVO  sesión MCP + viewport + foco + capturas
  paso_buscar_matriz.py     # NUEVO  macro del formulario + F10 + Shift+F4
  paso_copiar_ficha.py      # NUEVO  ficha del edificio -> portapapeles -> columna 3
  paso_extraer.py           # NUEVO  (sale de ciclo.py) bloques de 15 filas
  paso_paginar.py           # NUEVO  (sale de pagina.py) AvPag + fin + volver
  paso_encabezar.py         # NUEVO  entrar/volver al formulario y al 5250
  datos.py                  # NUEVO  (sale de loop.py) direcciones.csv + ledger.csv
  orquestador.py            # NUEVO  (sale de loop.py) el flujo por direccion B0..B7
  loop.py                   # queda como CLI fina que delega en orquestador
  autonomo.py               # el lote: pre_vuelo + por_direccion (no cambia)
  estado.py  click_sel.py  tabla.py  rows.py  recepcion.py  traza.py  # no cambia
```

## Qué se va a cada módulo y qué puertas se quedan dentro

| Módulo | Función | Puertas que conserva | Decisión que toma |
| --- | --- | --- | --- |
| `paso_buscar_matriz.py` | `buscar(s, hwnd, det, parte1, parte2)` | G0 = el formulario se leyó bien (Calle/No.Casa correctos por OCR) | ¿el texto está donde debe? → reescribe una vez o `revisar` |
| `paso_copiar_ficha.py` | `copiar_ficha(s, hwnd)` → dict | la ficha tiene 3 líneas útiles | ¿hay ficha? → columna 3 o `sin_datos` |
| `paso_extraer.py` | `extraer(s, hwnd, ...)` | G1 = la columna Suscript tiene datos (o Jev dice que sí) · G2 = el destino tras el cambio de ventana (icono de la taskbar) no es el 5250 · G3 = el pegado se ve (diff ≥ 3000 px) | ¿copio, salto la página o reintento? |
| `paso_paginar.py` | `paginar(s, hwnd)` / `volver(s, hwnd)` | la señal `fin_libro` | ¿sigo de página, termino o me quedo? |
| `paso_encabezar.py` | `ir_al_formulario(s, hwnd)` / `ir_al_5250(s, hwnd)` | el estado de pantalla | ¿dónde estoy y cómo vuelvo? |
| `datos.py` | `lee_direcciones()`, `escribe_ficha()`, `ledger_*()`, `reanuda_desde()` | el contrato de 3 columnas y el upsert por id | ¿qué falta y por dónde sigo? |
| `orquestador.py` | `procesa(fila, hwnd, s, ...)` | B0..B7 y el semáforo | ¿sigo con la siguiente dirección? |

## Reglas de la refactorización

1. **Ninguna puerta se mueve de sitio.** Si el diff cambia un umbral, es un
   error: el umbral va con la acción que lo usa.
2. **Cada módulo se puede probar sin máquina.** Las funciones puras (decidir,
   normalizar, medir) quedan fuera de las async; lo que necesita Windows queda
   detrás de una llamada inyectable.
3. **El orquestador no toca el teclado.** Si aparece un `press_keys` en
   `orquestador.py`, es que algo no quedó en su módulo.
4. **`loop.py` no se borra.** Pasa a ser el CLI: `loop.main()` delega en
   `orquestador.main()`. El historial de git conserva el original.
5. **Un fallo de un módulo no tumba el lote.** Todos los pasos se llaman
   desde un `try/except Halt` que anota y sigue (el patrón `error_puntual`
   que ya existe).
6. **Cero cambios de contrato:** el CSV sigue con 3 columnas (`parte1;parte2;ficha`),
   el ledger sigue con sus 13 campos, y `datos/fichas_pendientes.csv` sigue
   siendo el respaldo cuando Excel tiene el CSV abierto.

## Orden de ejecución (WIP = 1)

| # | Paso | Cómo se verifica |
| --- | --- | --- |
| 1 | `datos.py` (extraer solo, sin cambiar comportamiento) | los 170 tests siguen verdes |
| 2 | `paso_encabezar.py` | tests nuevos + los 170 |
| 3 | `paso_paginar.py` | idem |
| 4 | `paso_extraer.py` | idem |
| 5 | `paso_copiar_ficha.py` | idem |
| 6 | `paso_buscar_matriz.py` | idem |
| 7 | `orquestador.py` + `loop.py` como CLI | idem |
| 8 | **una corrida real de 1 dirección** (D05, la que falta) | hoja + ficha + ledger |
| 9 | `docs/TRACE_FUNCIONES.md` y `ESCALAMIENTO.md` actualizados | revisión |

En el paso 8 se verifica con la dirección que falta: si D05 entra bien en la
hoja y su ficha queda en la columna 3, la modularización no rompió nada.

## Lo que NO se toca

- Los umbrales medidos (G1 tinta 40 px, G3 diff 3000 px, Jev ≥ 0.6, `MAX_PAGINAS` 40).
- `estado.py`, `click_sel.py`, `tabla.py`, `rows.py` (percepción; ya están probados).
- El ledger y sus reglas de reanudación.
- `autonomo.py` (el lote) salvo para importar los módulos nuevos.
