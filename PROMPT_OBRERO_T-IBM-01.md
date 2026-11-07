# FROZEN WORKER PROMPT — T-IBM-01 (IBM-matriz → Chrome loop)

> Model-facing prompt. English. Frozen 2026-10-26. Do not edit after go —
> errata go at the top of the launcher message, never in this file.

## Objective
Process every `pending` row in `datos/datos.csv`: find its matriz account
on the remote IBM terminal (green screen, via AnyDesk MCP), OCR-read the
subscriber address rows, and type them into the ready Chrome spreadsheet,
cell by cell. One row = one subscriber. Done = all rows terminal
(`done|failed|not-found`), ledger complete, zero pastes in the wrong window.

## Allowed scope
- Files: `datos/datos.csv` (read), `datos/ledger.csv` (write),
  `tools/verifications/` + `evidencia/` (write), `TABLA_RANGOS.md` (read).
- MCP tools: `get_system_status`, `select_anydesk_window`,
  `initialize_session`, `write_to_anydesk` (ALWAYS `wrap=False` — IBM and
  Chrome are NOT PowerShell), `press_keys` (ONLY `tab`, `add`, `f10`,
  `["shift","f4"]`, `["alt","tab"]`), `read_from_anydesk`,
  `capture_screenshot`, `check_health`, `log_step_result`, `export_session`.
- FORBIDDEN: Enter (`press_keys` refuses it in code — never attempt),
  secrets/credentials, any key outside the allowlist, operating outside the
  pinned window, inventing addresses.

## Loop per item (no skipping)
1. Read row `i` (id, direccion_parte1, direccion_parte2, comuna,
   cuenta_matriz_esperada). Record `hora_inicio`. Field map: parte1 →
   calle field, parte2 → no-casa field, numpad `+` after each part.
2. Screenshot IBM → OCR → compare vs expected. Count each read in
   `paginas_vistas`.
3. Gates: G1 OCR legibility ≥ Fase-1 threshold · G2 address similarity ≥ 0.90
   · G3 rows-to-paste 1–50. Failed gate = `esperar_operador`, stop item.
4. HUMAN APPROVAL before EVERY injection (Jev degraded mode). Format:
   `Step N — [desc] · Risk: low|med|high · Action: ... · Approve?`
   Wait for explicit yes. Max 1 retry, only with approval.
5. part1 (`wrap=False`) → verify → `add` → verify → part2 → verify →
   `add` → `f10` → `["shift","f4"]`.
6. Screenshot section → set copy range per TABLA_RANGOS.md → OCR read.
7. `["alt","tab"]` to Chrome → screenshot-verify sheet focus → type cells
   (Tab advance) → re-read cells, compare vs source → `["alt","tab"]` back.
8. Ledger row: `done` (filas_copiadas + evidence) · `not-found` (absent in
   IBM, no retry) · `failed` (note in `notas`). Record `hora_fin`.
9. REPORTA per item (see format below).

## Executable acceptance (commands + expected output, never adjectives)
- `Test-Path datos/datos.csv` → True, `Import-Csv` row count = N.
- Every ledger row terminal (no `pending`) after the run.
- `check_health` → ok|warning (never degraded mid-run without escalation).
- Zero values typed while focus was outside the pinned window
  (verified by screenshot before each paste batch).

## Reading budget
Max ~10 exploratory reads. No archaeology of historic dossiers.

## REPORTA (end of run)
```text
REPORTA
- Items: done X / not-found Y / failed Z (ids listed)
- Pastes in wrong window: 0 | <list + cause>
- Gates tripped: <list | NONE>
- Out of scope: NONE | <list + justification>
- Dossier: tools/verifications/cierre-piloto.md
- Ledger: datos/ledger.csv (+ evidencia/ files)
- Risks/debt: <list | NONE>
```
