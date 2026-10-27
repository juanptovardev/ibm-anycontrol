# ESTADO_ORQUESTACION — bitácora append-only

No se edita el pasado: se **agrega** al final. Cada entrada lleva fecha, eventos
y verificaciones. Creado: 2026-10-27.

---

## 2026-10-27 — Línea base del motor 5250

**Estado**: E0 (humano valida cada paso). E1 bloqueada por el pegado en Chrome.

**Entregado**
- `tools/estado.py` — captura 1:1 → Tesseract → reglas puras → Jev si duda.
  Estados: `formulario | cuenta_matriz | sin_coincidencia | error | None`.
- `tools/tabla.py` — parser del listado CONSULTA UNIDADES (anclado a la derecha),
  normalización OCR por campo.
- `tools/paginar.py` — AvPág con paradas (suscriptores / fin de libro / tope /
  estado ambiguo).
- `tools/loop.py` — ciclo por dirección, blindaje B1..B7, ledger append-only.
- `tools/_jev.py` — cliente Jev por `curl` (clave en archivo temporal, fuera del argv).
- `tools/_mcp.py` — transporte MCP compartido (env-overridable, exit codes).
- `tests/` — 54 tests verdes.

**Commits**: `b57815f` (motor), `007b7d4` (umbral Jev), `5923c46` (tools 1:1),
`71adb59` (review tools), `23f3678` (tools read-only).

**Verificado en vivo**
- Captura 1:1 del viewport remoto: OK (PrintWindow, sobrevive a oclusión).
- OCR 5250 sin reescalar: 10/10 tokens (psm 6, x1). Con zoom x2: 9/10.
- Layout real del listado: `Direccion | Apto | Com | Div | Nodo | Suscript | Est`.
  El **Suscript es la penúltima** columna; el código de Nodo se repite y no es
  un suscriptor.
- Blindaje: con la pantalla remota en un portal web, el motor devolvió
  `estado=None`, confianza 0.32 y abortó **sin teclear**.

**Pendiente**
1. Pegado en Chrome (batch T-IBM-03) — falta contrato de columnas del operador.
2. OCR de la columna SUSCRIPTOR a 1:1 (la captura chica garblea dígitos:
   `soBs7ss1` por `50867551`).
3. Verificar si el salto a unidades entra con `shift+f4` o con `f16` directo.
4. Jev free da 429 → hoy el gate son las reglas; Jev queda de segunda opinión.

**Riesgos**
- El hwnd de AnyDesk y el del viewport child **cambian por sesión** → resolver
  siempre con `window_manager.find_viewport(root)`, nunca cachear.
- La ventana remota la redimensiona el operador → toda coordenada cacheada muere:
  re-medir (`tools/rows.py`) antes de cada clic.
- `Ctrl+C` no viaja por AnyDesk → el freno real es cerrar la sesión o matar el
  proceso Python; el ledger permite reanudar sin repetir.

---

## 2026-10-27 — Gobierno del repo

Creados los documentos de gobernanza: `GUIA_ORQUESTACION_IA.md`,
`EXECUTION_BATCHES.md`, `ESTADO_ORQUESTACION.md`, `TRACE_FUNCIONES.md` y
`docs/adr/` (ADR-0001..ADR-0006).
