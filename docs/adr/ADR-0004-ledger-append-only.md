# ADR-0004 — Ledger append-only e idempotencia por item

- **Fecha**: 2026-10-27
- **Estado**: Aceptada
- **Ámbito**: `dev/matriz-ibm-agent`

> **Superado por ADR-0007 (2026-11-19).** El ledger hace upsert por id con
> escritura atómica; no hubo nunca una fila por intento fallido. Este documento
> se conserva como historial.

## Contexto
El ciclo puede cortarse (AnyDesk cae, la licencia expira, el operador interrumpe,
falta la red). Rehacer la tanda desde cero duplica pegados en la hoja de Google
Sheets, que es el daño irreversible de este flujo.

## Decisión
- `datos/ledger.csv` es **append-only**: cada intento (incluido el fallido)
  escribe una fila; nunca se reescribe una fila anterior.
- La lectura (`ledger_leido`) toma la **última** fila por `id` → estado actual.
- Un item con estado `ok` no se reprocesa (idempotencia, blindaje B7).
- Cada fila guarda evidencia: `evidencia/` (capturas 1:1) + `notas`.

## Consecuencias
- Positivo: reanudar es natural (`python tools/loop.py <hwnd>` salta lo `ok`).
- Positivo: el historial completo permite auditar cuánto costó cada item y
  distinguir "no se encontró" de "falló el sistema".
- Positivo: `filas_copiadas` + `paginas_vistas` dan el rendimiento real.
- Negativo: el ledger crece y hay que deduplicar al leer; el formato CSV con
  comas en `notas` obliga a citarlas (se hace con el módulo `csv`).
- Negativo: no hay "deshacer": un `ok` con pegado erróneo se corrige a mano en
  la hoja (decisión humana).
