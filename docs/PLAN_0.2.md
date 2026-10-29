# Plan 0.2 (sobre 0.1) y hoja de ruta a 0.3

Esquema de versiones acordado con el operador:

| Version | Rama        | Donde vive                          | Estado                          |
| ------- | ----------- | ----------------------------------- | ------------------------------- |
| 0.1     | `v0.1`      | worktree `dev/matriz-ibm-agent-0.1` | CONGELADO y funcionando (tag `0.1`) |
| 0.2     | `v0.2`      | `dev/matriz-ibm-agent`              | planificado, pendiente de aprobacion |
| 0.3     | `v0.3`      | por crear                           | turnos futuros                  |

Regla de trabajo: **un cambio a la vez, con aprobacion del operador**, y sin
lanzar pilotos hasta que el operador lo autorice.

---

## 0.2 — que se anade (3 cambios)

### 0.2.1 Ledger con el formato correcto

**Problema medido**: `datos/ledger.csv` se escribe con coma (separador por
defecto de `csv.writer`) mientras `datos/direcciones.csv` usa `;`. En Excel en
espanol el separador es `;`, asi que el ledger se abre en UNA sola columna.

**Cambio**: `loop.ledger_escribe` escribe con `delimiter=";"`, `utf-8-sig` (BOM)
y `newline=""` (CRLF) — el mismo contrato que `loop.escribe_ficha`. Se actualiza
el lector (`ledger_leido`, `ledger_en_curso`) y se migra el fichero existente.

**Aceptacion**: test que escribe una fila y la relee con
`csv.DictReader(delimiter=";")` y comprueba los 13 campos; el CSV resultante
empieza por BOM y no tiene LF sueltos.

### 0.2.2 Contrato de columnas de la hoja (con un clic)

**Problema medido**: el pegado depende de donde quedo el cursor en la hoja. No
hay ningun contrato de que columna es la que se pega.

**Cambio**:
1. Leer la fila 1 de la hoja (cabecera) una vez por corrida.
2. Deducir el mapa de columnas: que columna es DIRECCION, cual EDIFICIO, cual
   SUSCRIPTOR (las que ya se observaron en vivo: A=DIRECCION, B=EDIFICIO,
   I/J=SUSCRIPTOR). Si la cabecera no coincide con lo esperado, **error
   explicito y no se pega** (falla cerrado, como el resto).
3. Antes de cada pegado, **un clic en la celda de destino** que dicta el
   contrato (columna DIRECCION, primera fila libre del bloque), en vez de
   depender del cursor.

**Aceptacion**: test con la cabecera real -> mapa correcto; test con otra
cabecera -> error explicito y no se pega; test del calculo de la fila destino.

### 0.2.3 Limpieza del campo Nombre sin 24 espacios

**Problema medido**: hoy el campo Nombre se limpia escribiendo 24 espacios
(truco del emulador: `delete` no borra y `home` salta al primer campo). Son 5.5 s
por direccion y es fragil.

**Secuencia que da el operador** (sustituye al truco):

```
clic en la celda 1 del campo Nombre
flecha derecha
flecha izquierda
suprimir
+ (numpad add = Field Exit)   -> limpia y salta al campo Calle
```

**Cambio**: `loop.buscar` usa esa secuencia en vez de los 24 espacios, y el
resto de la macro (parte1, `+`, parte2, `+`, BOG, `+`, TVC, F10) queda igual.

**Aceptacion**: test de la secuencia exacta (orden de teclas y numero de
llamadas) + validacion en vivo en la fase de piloto (que la tinta caiga en Calle
y no en Nombre, que es lo que ya mide `verifica_texto`).

---

## Descartado por decision del operador

- **Verificacion post-pegado por contenido** (releer la celda pegada y
  compararla con el origen): se descarta por sobrecosto en tiempo. El pegado se
  valida como hasta ahora (diff de pixeles + G2/G3).

---

## Lo que 0.2 NO toca

La extraccion, la copia, el pegado, la paginacion, la deteccion de fin de
archivo, la reanudacion desde el ledger y el blindaje quedan igual. 0.2 solo
mejora tres puntos, sin cambiar el comportamiento del flujo.

## Orden de trabajo en 0.2

| # | Cambio                      | Riesgo | Como se valida                        |
| - | --------------------------- | ------ | ------------------------------------- |
| 1 | 0.2.1 Ledger `;`            | bajo   | suite automatica                     |
| 2 | 0.2.3 Limpieza del Nombre   | medio  | suite + piloto en vivo (1 direccion) |
| 3 | 0.2.2 Contrato de columnas  | medio  | suite + piloto en vivo (1 direccion) |

## 0.3 (turnos futuros)

**Solo modularizacion de 0.2**, sin cambios de comportamiento:

```
tools/matriz_buscar.py     -> busca el edificio y devuelve la ficha
tools/matriz_ficha.py      -> lee la ficha y la escribe en el CSV
tools/matriz_extraer.py    -> extrae, copia, pega y pagina
tools/orquesta.py          -> el estado machine (traza + semaforo) actual
```

Con las condiciones logicas intactas: el semaforo, el blindaje, el ledger y la
reanudacion siguen siendo los mismos, solo cambian de archivo.
