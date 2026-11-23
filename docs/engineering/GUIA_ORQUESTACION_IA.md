# Guía de Orquestación IA — matriz-ibm-agent

Metodología **ORCA** aplicada a este repo: OPERACIÓN → MERGE → AUDIT → CIERRE.
El hilo principal (el agente en la CLI) es delgado: delega la pantalla, re-verifica
lo que dice el obrero y nunca acepta un claim sin re-ejecutarlo.

- Creado: 2026-10-27
- Stack: Python 3.14 (venv de `dev/mcp-anydesk`), MCP por stdio (`mcp>=1.0,<2`),
  Tesseract 5.4.0, OpenCV, Hermes (perfil `matriz-ops`) como runtime del obrero.

---

## 1. Capas del sistema (y quién manda en cada una)

| Capa | Archivo | Responsabilidad |
|------|---------|------------------|
| Decisión de pantalla | `tools/estado.py` | ¿Qué pantalla es? (reglas puras primero, Jev si duda) |
| Lectura de datos | `tools/tabla.py`, `tools/paginar.py` | Filas de suscriptores, paginación del libro |
| Ejecución mecánica | `tools/matriz_buscar.py`, `tools/ciclo.py`, `tools/loop.py` | Macro 5250 + ciclo por dirección con blindaje |
| Transporte | `tools/_mcp.py`, `dev/mcp-anydesk` | Sesión MCP, foco, teclas, clics |
| Segunda opinión | `tools/_jev.py` | Jev 1.13 free: desempate por texto, no ve imágenes |
| Bitácora | `datos/ledger.csv`, `evidencia/` | Una fila por dirección, upsert por id |

**Regla de oro**: la velocidad NO depende de un modelo. Las reglas deterministas
resuelven el 95% de los casos en <5 ms; Jev (~300 ms) solo interviene cuando el
texto es ambiguo, y su confianza <0.6 significa "no clasifico" → el ciclo aborta.

---

## 2. Reglas de oro (no negociables)

1. **Aislamiento físico**: una tarea = una rama = un worktree. Nadie opera la
   pantalla desde dos sitios.
2. **Nadie califica su propio trabajo**: obrero ≠ rematador ≠ auditor.
3. **Evidencia re-ejecutada > claims**: no se acepta un número sin re-ejecutarlo
   con comandos propios.
4. **Sin dossier no hay merge.**
5. **Erratas en el launcher, jamás en el prompt congelado.**
6. **STOP + escalar, no improvisar** (§6).
7. **AI Stack obligatorio**: Ponytail (YAGNI antes de código), anti-slop,
   context-mode Think-in-Code, headroom MCP. Health check antes de lanzar obreros.

---

## 3. Fases

### F0 — Intake
Objetivo, alcance, criterios de aceptación **ejecutables** (comando + output
esperado), stack y versiones. Nada implícito: cada decisión queda en `docs/adr/`.

### F1 — PLAN
Descomponer en Work Packages secuenciales (**WIP = 1**). Cada WP tiene un prompt
congelado en `EXECUTION_BATCHES.md` con alcance exacto (archivos permitidos),
prohibiciones y criterios de aceptación con comando. Se pide go/no-go al humano.

### F2 — ORCA (ejecución)
1. Precondiciones: repo limpio, baseline verde, smoke del proveedor.
2. Aislamiento creado por el orquestador (nunca por el obrero).
3. Launcher re-ejecutable, log en disco, modelo del obrero distinto del principal.
4. Watchdog: si el log no escribe >5 min y no hay proceso vivo → matar por árbol
   (nunca por nombre de proceso) y relanzar el mismo prompt con nota de retome.
5. Merge verificado: suite del paquete tocado + re-ejecución de los criterios.

### F3 — CIERRE ciego
Sesión fresca, modelo distinto al del obrero: veredicto
**CERRADA / CERRADA-CON-RESERVAS / RECHAZADA** + escalados + SHAs.

### F4 — AUDIT y reporte
Re-ejecutar los números clave, actualizar `ESTADO_ORQUESTACION.md` (append-only)
y auto-reportar al humano: veredicto + SHAs + reservas.

---

## 4. Blindaje del ciclo (B1–B7)

| # | Regla | Dónde |
|---|-------|-------|
| B1 | No se teclea a ciegas: la pantalla debe estar en `formulario` | `loop.procesa` |
| B2 | No se pulsa F10 sin verificar que el texto quedó en Calle y **no** en Nombre | `loop.verifica_texto` |
| B3 | Si el estado tras la búsqueda no es el esperado, el item se aborta | `loop.espera_estado` |
| B4 | El foco lo vigila el server (focus guard) → si una ventana local roba el foco, la llamada MCP falla y el item se marca error | `mcp-anydesk` + `loop` |
| B5 | Máximo 1 reintento por item | `loop.REINTENTOS` |
| B6 | Todo item deja rastro: fila en ledger + captura en `evidencia/` | `loop.ledger_escribe` |
| B7 | Idempotencia: lo que ya está `ok` no se reprocesa | `loop.ledger_leido` |

Regla adicional heredada del trabajo con el operador: **el humano puede tocar la
pantalla mientras corre el agente**. Por eso toda escritura va precedida de B1 y
seguida de B2: si hay interferencia, se detecta y se aborta en vez de escribir en
el campo equivocado.

---

## 5. Contratos congelados

- `datos/direcciones.csv` (entrada): `parte1;parte2;ficha` (ids posicionales D01..)
- `datos/ledger.csv` (salida, upsert por id): `id,direccion_parte1,direccion_parte2,comuna,cuenta_matriz_esperada,estado,paginas_vistas,filas_copiadas,hora_inicio,hora_fin,evidencia,notas,reintentos`
  - La lectura toma la fila del `id`.
- Estados de pantalla: `formulario | cuenta_matriz | sin_coincidencia | error | None`
  (`None` = "no pude clasificar", nunca "la pantalla está mal").

---

## 6. STOP y escalar (no improvisar)

1. Aceptación fallida 2 veces en la misma tarea.
2. Un test cambia tras un refactor → se revierte el refactor, no el test.
3. Archivo fuera de alcance modificado sin declarar en REPORTA.
4. Conflicto de merge o suite roja post-merge.
5. Proveedor caído sin vía alternativa sana (Jev 429 → reglas + aprobación manual).
6. Desviación contra la Directiva o el Quality Manual.

**Regla de no escalar**: si un item termina en `error` 2 veces seguidas → parar la
tanda. No "reintentar más fuerte".

---

## 7. SOLO-HUMANO (pedir, jamás ejecutar)

- Credenciales, secretos, API keys.
- Dinero: planes, compras, presupuesto de tokens.
- Borrado irreversible fuera de `evidencia/`/regenerables.
- Push a remoto nuevo/público o release público.
- **Traer el emulador 5250 al frente y mantener la sesión AnyDesk viva**: es
  requisito de E0/E1 y lo hace el operador.
- Validación final de la hoja pegada.

---

## 8. Formatos obligatorios

### REPORTA (final de cada obrero)
```text
REPORTA
- SHA: <sha corto>
- Aceptación: <comando + output pegado, por cada criterio>
- Archivos tocados: <lista>
- Fuera de alcance: NINGUNO | <lista + justificación>
- Dossier: tools/verifications/<nombre>.md
- TRACE_FUNCIONES: entradas añadidas/reutilizadas | NINGUNA
- Riesgos/deuda detectada: <lista | NINGUNO>
```

### ORCHESTRA REPORT (final de cada etapa)
```text
ORCHESTRA REPORT
- Etapa: N
- Worktrees: <limpios / mantenidos>
- Commits: <shas>
- Tests: N/N
- Reservas: <lista | NINGUNA>
```

---

## 9. Puertas de operación (E0–E3)

| Puerta | N | Modo | Criterio de avance |
|--------|---|------|--------------------|
| E0 | 1 | Humano valida cada paso | 1 ciclo completo con ledger y evidencia |
| E1 | 5 | Loop automático, humano revisa ledger | 5/5 items con estado conocido, 0 filas perdidas |
| E2 | 20 | Loop automático + muestreo 20% | 20/20 en ledger, 0 duplicados en la hoja, tiempo estable (±30%) |
| E3 | 100+ | Lotes de 20, checkpoint por item | 0 losses, ≥1 item/15 s, revisión semanal del ledger |

---

## 10. Reutilización (regla del 80%)

Antes de escribir código nuevo: buscar en `TRACE_FUNCIONES.md` + `grep` en
`tools/*` + exports de `dev/mcp-anydesk`. Si el repo ya resuelve ≥80% → reutilizar.
Registrar la entrada nueva en el mismo commit. Duplicado funcional = rechazo en
auditoría.
