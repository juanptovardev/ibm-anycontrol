# Versionado del agente 5250 — 0.1 / 0.2 / 0.3

Esquema acordado con el operador:

| Version | Rama   | Donde vive                          | Estado                                     |
| ------- | ------ | ----------------------------------- | ------------------------------------------ |
| 0.1     | `v0.1` | worktree `dev/matriz-ibm-agent-0.1` | CONGELADO y funcionando (tag `0.1`, 186 tests) |
| 0.2     | `v0.2` | `dev/matriz-ibm-agent`              | IMPLEMENTADO (199 tests), pendiente de piloto |
| 0.3     | `v0.3` | por crear                           | turnos futuros                             |

Regla de trabajo: **un cambio a la vez, con aprobacion del operador**, y sin
lanzar pilotos hasta que el operador lo autorice.

---

## 0.1 — la linea base congelada

Tag `0.1`, rama `v0.1`, copia de trabajo en `dev/matriz-ibm-agent-0.1` con sus
datos (`direcciones.csv`, `ledger.csv`, `datos.csv`). Es el sistema que pasteo
5 direcciones, 765 filas, con fin de archivo automatico y reanudacion sola.

## 0.2 — lo que se implemento

### 0.2.1 El ledger como tabla (una fila por direccion) — HECHO

**Problema que reporto el operador**: el ledger append-only (una fila por PAGINA
pegada) se leia "como una lista vertical" con la misma direccion repetida.

**Solucion**: `ledger_escribe` hace UPSERT por id (una fila por direccion, con su
estado actual), con escritura atomica (temporal + `os.replace`) y formato de
Excel en espanol: `;` + BOM (`utf-8-sig`) + CRLF.

- `_sep_ledger(ruta)`: detecta `;` (nuevo) o `,` (antiguo) → el ledger viejo se
  lee igual, la migracion es transparente.
- `es_resumable(fila)`: regla UNICA de reanudable = estado `en_curso` o error con
  `paginas_vistas > 0`. `ok` y `no_encontrado` nunca son reanudables.
- El ledger hereda el punto de reanudacion de la fila anterior cuando la nueva
  dice 0 y es la MISMA direccion: el fallo final no borra las paginas ya pegadas.
- El historial completo (una linea por pagina) queda en `datos/traza.jsonl`,
  que es append-only. No se pierde nada.
- El `datos/ledger.csv` existente se migro de 62 filas a 5 (una por direccion).

### 0.2.2 Limpieza del campo Nombre sin 24 espacios — HECHO

La secuencia del operador sustituye al truco de escribir 24 espacios:

```
clic en la celda 1 del campo Nombre
flecha derecha
flecha izquierda
suprimir
+ (numpad add = Field Exit)   -> limpia y deja el cursor en Calle
```

En Calle, el mismo patron antes de escribir la parte 1. Se ahorran ~5,5 s por
direccion y se quita la dependencia de escribir espacios en un campo que no
borra.

**Riesgo conocido**: `delete` no borra en este emulador (medido antes). Si en el
piloto el campo Nombre no queda limpio, hay que volver a los 24 espacios. El
piloto lo valida.

### Descartado por decision del operador

- **Verificacion post-pegado por contenido**: se descarta por sobrecosto en
  tiempo. El pegado se valida como hasta ahora (diff de pixeles + puertas G2/G3).

### Movido a 0.3

- El **contrato de columnas de la hoja** (leer la cabecera, deducir el mapa
  DIRECCION / EDIFICIO / SUSCRIPTOR y hacer un clic en la celda de destino antes
  de pegar) sale de 0.2 y pasa a 0.3.

---

## 0.3 — turnos futuros

1. **Modularizacion de 0.2**, sin cambios de comportamiento:

```
tools/matriz_buscar.py     -> busca el edificio y devuelve la ficha
tools/matriz_ficha.py      -> lee la ficha y la escribe en el CSV
tools/matriz_extraer.py    -> extrae, copia, pega y pagina
tools/orquesta.py          -> el estado machine (traza + semaforo) actual
```

2. **Contrato de columnas de la hoja**: leer la fila 1 una vez por corrida,
   deducir el mapa de columnas, y **un clic en la celda de destino** antes de
   cada pegado (en vez de depender de donde quedo el cursor). Si la cabecera no
   coincide con lo esperado: error explicito y no se pega (falla cerrado).

Con las condiciones logicas intactas: el semaforo, el blindaje, el ledger y la
reanudacion siguen siendo los mismos, solo cambian de archivo.
