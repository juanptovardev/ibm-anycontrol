# RONDA DE ANÁLISIS Y PRUEBAS — agente matriz IBM (terminal verde 5250)

Rol: yo actúo como obrero. Tú eres operador/supervisor (pre-login, ventana AnyDesk arriba, aprobación).
Reglas duras: nunca toco secretos/logins/2FA · nunca Enter · 1 inyección = 1 paso · 1 reintento máximo con aprobación (se cuenta en columna `reintentos` del ledger) · sin éxito asumido sin leer output · stop ante foco perdido, OCR ilegible 2 veces seguidas o gate < umbral.

## FASE 0 — Análisis estático (conmigo, sin tocar nada)

Me envías 5 pantallazos (tapa PII si quieres). Por cada uno extraigo lo indicado:

| # | Pantallazo | Qué extraigo yo |
|---|-----------|-----------------|
| P1 | IBM: pantalla de búsqueda de cuenta matriz (vacía) | Campos, orden de tabulación, etiquetas exactas, posición fila/col de cada campo |
| P2 | IBM: cuenta matriz con resultados (parte 1 y parte 2 visibles) | Formato de parte 1 / parte 2, dónde cae el `+` numérico, filas por página |
| P3 | IBM: sección post F10 + Shift+F4 (de dónde a dónde se copia) | Rango exacto de copia: fila/col inicio → fila/col fin, marcadores de sección |
| P4 | Chrome: hoja de cálculo destino | Columnas fijas, fila por suscriptor, celda inicial, formato esperado |
| P5 | Ventana AnyDesk "Oficina - AnyDesk" en tu PC | Confirmo que hay sesión viva para la fase en vivo |

Salida de Fase 0: `TABLA_RANGOS.md` (sección → rango copia → slot destino) + reglas del parser (etiquetas ancla por fila/col). Sin P1–P5 no hay fase en vivo.

## FASE 1 — Salud local (supervisada, puede robar foco 2 segundos)

Prerrequisitos (medidos el 2026-10-26, ver `tools/verifications/fase1-salud.md`):
- AnyDesk debe estar CORRIENDO en este PC. Medido: `anydesk_windows: []`, `select_anydesk_window` → "No AnyDesk sessions detected". Sin esto, Fases 2–3 bloqueadas.
- Jev medido CAÍDO: `probe_http_status: 502` en `jev_status`, `jev_gate`, `jev_classify` y `jev_score` (todos HTTP 502). Mientras siga así, rige modo degradado: solo confirmación humana, sin auto-inyección (ver ADR pendiente). Reintentar `jev_status`; si da 402 → hacer check-in diario y repetir.

Comandos ejecutables con output esperado (no adjetivos):

1. `python test_mcp_smoke.py` en `dev/mcp-anydesk` → esperado: lista 19 tools, `ocr_capable=true/false` REGISTRADO por perfil (resuelve inconsistencia #2).
2. `python test_mcp_smoke.py` en `dev/jev-gate` → esperado: 6 tools, `key_present=true`.
3. Llamar `jev_score` con un texto OCR real corto → esperado: REGISTRAR escala real devuelta (resuelve inconsistencia #1: ¿0–2 o 2–10?).
4. Llamar `jev_status` → esperado: `model=free/jev-1.13`, `http_status=200` (402 = hacer check-in diario primero; 502 = modo degradado).
5. Primera lectura OCR real sobre la pantalla IBM en vivo → esperado: REGISTRAR confianza media y fijar umbral G1 (p.ej. media−0.05) en `tools/verifications/fase1-salud.md` (resuelve inconsistencia #5a).

Aceptación Fase 1: 5/5 outputs registrados en `tools/verifications/fase1-salud.md` (crear `tools/verifications/` si no existe). Si 403/401 → escalar (inconsistencia #3 sigue abierta → T1 de modelos).

## FASE 2 — Spike de teclas T0 (construido 2026-10-26: `press_keys` v3.6.0 en `dev/mcp-anydesk`)

Estado: tool construido y verificado en local SIN regresión (19 tools en smoke). Falta la prueba viva con tu aprobación, tecla por tecla.

Reglas del tool (en código, no por convención): Enter SIEMPRE rechazado · Ctrl+C rechazado (remite a `send_cancel`) · modificadores held (shift/ctrl/alt) + tap + release.

Orden de pruebas vivas (yo ejecuto una por vez, tú apruebas, verificamos por pantallazo):

| # | Tecla | Qué espero ver | Riesgo |
|---|-------|----------------|--------|
| T0a | Tab | foco se mueve / nada se rompe | bajo |
| T0b | F10 | menú enfocado / nada se rompe | bajo |
| T0c | Alt+Tab ida + vuelta | ¿cambió el PC remoto o el local? | MEDIO: AnyDesk puede retener Alt+Tab local — verificar lado por pantallazo |
| T2 | `+` numérico (add) | solo en contexto IBM | diferido a pantalla IBM |
| T6 | Shift+F4 | solo en contexto IBM | diferido a pantalla IBM |

T1/T3/T4 (texto Unicode) ya probados: `whoami` inyectado y leído de vuelta en vivo.

## DECISIÓN 2026-10-26 (operador): T0 sin pruebas vivas
T0a–T0c quedan ACEPTADOS por declaración del operador ("las combinaciones se
detectan bien"), sin prueba viva a su pedido. Registro honesto: veredicto =
aceptado-por-operador, NO medido. La primera tecla real en Fase 3 confirma el
mecanismo o dispara STOP + rediseño. T2/T6 siguen diferidos a pantalla IBM.

Criterio go: T0a–T0c PASS → el mecanismo viaja → sigue el agente personalizado (perfil matriz-ops + runbook). Si Alt+Tab queda local → plan B (click en barra de tareas o secuencia que tú dictes). T2/T6 se validan contra IBM real en Fase 3.

## DECISIÓN 2026-10-26: Jev manual + orden T0 → agente

- Jev por API bloqueado (429 gratis / 401 pago, causa raíz: entitlement de cuenta, cliente auditado limpio). Rige modo degradado: el LLM propone, TÚ apruebas cada inyección. Ledger registra `aprobado_por: humano`.
- Orden: T0 (teclas) ANTES que agente personalizado. Sin manos probadas, el agente sería diseño a ciegas.

## FASE 3 — Piloto N≤5 con ledger (yo como obrero, tú aprobando cada inyección)

Entrada: copia `datos/datos_ejemplo.csv` → `datos/datos.csv` con los N datos reales (6 columnas: id, direccion_parte1, direccion_parte2, comuna, cuenta_matriz_esperada, nota). Sin `datos/datos.csv` no arranca la fase. Mapeo IBM: parte1 → campo calle, parte2 → campo no-casa, `+` numérico al final de cada parte. Verificar antes de arrancar: `(Import-Csv datos/datos.csv | Get-Member -MemberType NoteProperty).Name` debe ser exactamente `id,direccion_parte1,direccion_parte2,comuna,cuenta_matriz_esperada,nota`, y cada fila debe tener 6 campos: `Import-Csv datos/datos.csv | ForEach-Object { if (@($_.PSObject.Properties).Count -ne 6) { throw "Fila mala: $($_.id)" } }`. La columna `nota` de entrada es solo contexto humano, nunca se inyecta a IBM (las notas del run van en `notas` del ledger). Filas piloto pueden traer `cuenta_matriz_esperada` vacía (entonces la verificación de cuenta es solo visual/operador, no G2).

Por cada ítem `i` del `datos/datos.csv`, ejecuto exactamente esto:

1. Leo la fila `i` (id, direccion_parte1, direccion_parte2, comuna, cuenta_matriz_esperada). Registro `hora_inicio`.
2. Pantallazo IBM → OCR → comparo contra lo esperado. Cuento en `paginas_vistas` cada pantallazo IBM leído.
3. Gates: G1 legibilidad OCR ≥ umbral fijado en Fase 1 (paso 5) · G2 similitud dirección ≥ 0.90 · G3 filas a pegar 1–50. Si un gate falla → `esperar_operador`, no avanzo.
4. `jev_classify` [ejecutar, esperar_operador, abortar] antes de CADA inyección (en modo degradado: tu aprobación manual reemplaza este paso).
5. Inyecto parte 1 → verifico por pantallazo → `+` numérico → verifico → parte 2 → verifico → `+` → F10 → Shift+F4 → pantallazo sección → defino rango según TABLA_RANGOS → leo (OCR) → Alt+Tab a Chrome → verifico foco en hoja → escribo celda por celda (avance con Tab) → releo celdas y comparo contra origen → Alt+Tab de vuelta.
6. Marco `datos/ledger.csv` (columnas ya definidas; `reintentos` default 0, +1 por reintento aprobado) y registro `hora_fin`: `done` (con filas_copiadas + evidencia) · `not-found` (no apareció: esperado, sin reintento) · `failed` (con nota en `notas`).
7. REPORTA por ítem: id + estado + pantallazos clave + gates + fuera de alcance.

Aceptación Fase 3: 5/5 ítems con estado final distinto de `pending` + 0 pegados en ventana equivocada + ledger y evidencia completos.

## FASE 4 — Veredicto

Tabla PASS/FAIL por fase + decisión única: PROCEDE a build completo / REDISEÑA (con qué cambio) / ESCALA a humano (con motivo). Sin veredicto no hay T3/T4/T5 del proyecto.

## INCONSISTENCIAS QUE ESTA RONDA RESUELVE

| # | Inconsistencia | Dónde se resuelve | Cómo queda fijado |
|---|----------------|-------------------|-------------------|
| 1 | Escala jev_score: 0–2 (memoria) vs 2–10 (docstring/skill) | Fase 1, paso 3 | Se registra la escala REAL devuelta y se fija en ADR |
| 2 | Registro MCP divergente (wrapper solo en anydesk-ops) | Fase 1, paso 1 | Se registra `ocr_capable` por perfil; se usa el perfil que dé true |
| 3 | Modelo rápido + 403 fuera de OpenCode | Fase 1 (+ T1 del proyecto) | Smoke decide: NVIDIA NIM verificado o fix del 403 |
| 4 | VK combos eliminados vs teclas necesarias | Fase 2 (T0) | `press_keys` v3.6.0 construido; go = T0a–T0c PASS en vivo, si no rediseño |
| 5a | G1 sin umbral definible (ningún paso lo fijaba) | Fase 1, paso 5 | OCR real → confianza media → umbral G1 registrado en dossier |
| 5b | G1 ≥ 0.85 (subagente B) vs rutas 9-10/6-8 (skill) | Fase 1, paso 3 | Se unifica a la escala real medida |
| 6 | "Copiar" sin Ctrl+C posible | Fases 2–3 | Leer por OCR + escribir por Unicode; verificado por pantallazo |
| 7 | Jev caído (HTTP 502 medido 2026-10-26) vs SOUL "Jev obligatorio" | Fase 1 prerrequisitos | Modo degradado: aprobación manual reemplaza gates hasta que `jev_status` dé 200 |
| 8 | Tab no cambia de aplicación (T7 mezclaba ida + avance) | Fase 2 (tabla T7/T8/T9) | Ida a Chrome = Alt+Tab (T8); Tab solo avance interno (T7) |

Si ves alguna inconsistencia más, dime cuál y la agrego a la tabla con su fase de resolución.
