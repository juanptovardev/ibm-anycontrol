# Traza y semáforo

Dos piezas nuevas que convierten el sistema en algo legible y auditable.

## 1. Traza (`tools/traza.py`)

Cada herramienta reporta qué hizo. Se escribe en dos formatos:

| Archivo | Para quién |
|---|---|
| `datos/traza.jsonl` | máquina / Jev. Una línea JSON por evento. |
| `datos/traza.md` | humano. Tabla con hora, etapa, resultado, siguiente paso. |

Ambos son **append-only** y están en `.gitignore` (son datos de corrida).

Evento:

```json
{"ts": "2026-10-27 19:40:02", "run": "20261027-194002", "etapa": "estado",
 "resultado": "cuenta_matriz", "accion": "extraer", "detalle": "PILOTO-01 conf 0.95"}
```

Etapas: `entorno → pin → estado → buscar → extraer → volver → pagina →
reconectar → registrar → cierre`.

Consultas:

```powershell
python tools/traza.py            # últimos 20 eventos + PUNTO ACTUAL
python tools/traza.py --json     # el punto actual
python tools/traza.py --jev      # resumen compacto listo para el prompt de Jev
```

## 2. Semáforo (policía de tránsito)

Un mapa declarativo `(etapa, resultado) → acción`. Ninguna herramienta decide
sola: reporta y el semáforo manda. **Si falta la regla, se detiene** (fallar
cerrado, nunca improvisar).

```
estado=formulario      -> buscar
estado=cuenta_matriz   -> extraer
estado=fin_libro       -> cierre
estado=sin_coincidencia-> siguiente
estado=desconectado    -> reconectar
buscar=ok              -> extraer
extraer=ok             -> volver
volver=ok              -> pagina
pagina=cuenta_matriz   -> extraer      (otra página)
pagina=fin_libro       -> cierre       (matriz terminada)
reconectar=ok          -> estado
cierre=ok              -> siguiente
```

Agregar un `.py` nuevo = agregar su etapa y sus reglas en `traza.py`. Nada de
`if` sueltos repartidos por el código.

## 3. Fin de archivo (`fin_libro`)

El 5250 avisa al paginar más allá del último registro:

```
Giro hacia arriba o hacia abajo más allá del primer o último registro en el archivo
```

Se detecta por la **frase**, no por `F12=Anterior` (esa tecla puede estar en la
barra sin que la matriz haya terminado). Gana sobre `cuenta_matriz` porque el
listado sigue en pantalla pero ya no hay páginas.

## 4. Reconexión (`tools/vigia.py`)

La licencia gratuita de AnyDesk corta la sesión y dibuja un diálogo **local**:

```
ad_modal_dlg#283   'Conexión finalizada'
basic_button#286   'Repetir'      <- se pulsa este
```

Es una ventana local, así que el botón se busca por texto y se pulsa con clic
físico (AnyDesk al frente, cursor devuelto a su sitio). El OCR del viewport no
siempre lo ve: el modal es hermano del viewport, no hijo. Por eso `loop.py`
pregunta primero a la enumeración de ventanas.

Medido: tras pulsar Repetir el diálogo tarda ~10–30 s en cerrar → espera 25 s.
