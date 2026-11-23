# ADR-0007 — Ledger con upsert por id

- **Fecha**: 2026-11-19
- **Estado**: Aceptada
- **Supersede**: ADR-0004 (ledger append-only)
- **Ámbito**: `datos/ledger.csv`, `tools/loop.py`

## Contexto
ADR-0004 declaró el ledger append-only: una fila por intento y la lectura tomaba
la última fila del `id`. El código nunca implementó ese formato. `tools/loop.py`
escribe el ledger con `ledger_escribe()`, que busca la fila del `id` y la
actualiza; es una tabla de una fila por dirección.

## Decisión
- `datos/ledger.csv` es una tabla de 13 campos con **una fila por dirección**.
- `ledger_escribe()` hace **upsert por `id`**: reescribe la fila existente o
  añade una nueva si el `id` no está.
- La escritura es **atómica**: archivo temporal, `fsync`, `.bak` y `os.replace`.
  Si el proceso muere a mitad, el ledger no queda a medias.
- La reanudación sigue igual: un `id` con estado `ok` no se reprocesa.

## Consecuencias
- Positivo: el ledger no crece con los reintentos; el tamaño refleja el número de
  direcciones, no de intentos.
- Positivo: la escritura atómica protege el archivo ante cortes (AnyDesk, licencia,
  red, interrupción del operador).
- Neutro: se pierde el historial de intentos fallidos. El conteo de intentos vive
  en la columna de estado y en la traza, no en filas acumuladas.
- Negativo: corregir un `ok` con pegado erróneo sigue siendo manual en la hoja
  (igual que en ADR-0004).
