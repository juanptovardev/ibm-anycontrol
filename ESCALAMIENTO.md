# Escalamiento y blindaje — matriz-ibm-agent

Gobernanza completa: `docs/engineering/GUIA_ORQUESTACION_IA.md` (método ORCA) ·
`docs/engineering/EXECUTION_BATCHES.md` (prompts congelados) ·
`docs/engineering/ESTADO_ORQUESTACION.md` (bitácora) ·
`docs/engineering/TRACE_FUNCIONES.md` (catálogo anti-reescritura) ·
`docs/adr/` (decisiones) · `tools/verifications/dossier-motor-5250.md` (evidencia).

Motor: `tools/loop.py` (ciclo por dirección) + `tools/estado.py` (qué pantalla es) +
`tools/tabla.py` (qué dice el listado) + `tools/paginar.py` (AvPág) + `tools/_jev.py` (Jev).

---

## 1. Blindaje — reglas duras, cada una verificable

| # | Regla | Dónde | Cómo se rompe (y para) |
|---|-------|-------|------------------------|
| B1 | No se teclea a ciegas: la pantalla debe estar en `formulario` | `loop.procesa` | Si el estado no es `formulario`, el item se aborta con motivo. No se "intenta otra vez a ver" |
| B2 | No se pulsa F10 sin verificar que el texto quedó en Calle y **no** en Nombre | `loop.verifica_texto` (tinta por píxel) | Si la tinta está en Nombre → aborta antes de F10 |
| B3 | Si el estado tras la búsqueda no es el esperado, el item se aborta | `loop.espera_estado` | Distingue `sin_coincidencia` (resultado de negocio) de `error` (algo se rompió) |
| B4 | El foco lo vigila el server: si la ventana local roba el foco, la llamada MCP falla | `mcp-anydesk` focus guard | `Halt` inmediato: el item se marca error, no se sigue tecleando |
| B5 | Máximo 1 reintento por item, con la misma secuencia | `loop.REINTENTOS` | Al segundo fallo se abandona el item |
| B6 | Todo item deja rastro: fila en `datos/ledger.csv` + captura en `evidencia/` | `loop.ledger_escribe`, `pf.shot` | Bitácora append-only: cada intento es una fila |
| B7 | Idempotencia: lo que ya está `ok` no se reprocesa | `loop.ledger_leido` | Se puede relanzar la tanda sin duplicar trabajo |

**Extra (punto donde falló el ciclo manual):** el operador puede tocar la pantalla
mientras corre el agente. Eso invalida la posición del cursor. Por eso **toda**
escritura va precedida de B1 y seguida de B2: si el humano interfiere, el
detecta y aborta en vez de escribir en el campo equivocado.

---

## 2. Escalamiento — puertas y criterios de avance

| Puerta | N | Modo | Criterio para pasar a la siguiente |
|--------|---|------|----------------------------------|
| E0 | 1 | Humano valida cada paso (estado actual) | 1 ciclo completo con ledger y evidencia |
| E1 | 5 | Loop automático, humano revisa el ledger | 5/5 items con estado conocido, 0 filas perdidas |
| E2 | 20 | Loop automático + muestreo del 20% | 20/20 en ledger, 0 duplicados en la hoja, tiempo por item estable (±30%) |
| E3 | 100+ | Lotes de 20, checkpoint por item, reanudar | 0 losses, throughput >= 1 item/15 s, revisión semanal del ledger |

**Regla de no escalar**: si un item termina en `error` 2 veces seguidas → parar
la tanda. No "reintentar más fuerte". (Mismo criterio STOP del protocolo ORCA.)

---

## 3. Rendimiento medido (por item, 1 página)

| Paso | Coste |
|------|-------|
| Captura 1:1 (PrintWindow) | ~120 ms |
| OCR Tesseract (psm 6, x1) | ~150 ms |
| Clasificación por regla | < 5 ms |
| Jev (solo si la regla duda) | ~300 ms |
| Escribir parte1 + parte2 | ~1 s |
| AvPág + captura + OCR | ~700 ms por página |

Estimado: **6–12 s por dirección** (1 página), +1,2 s por página extra del libro.

---

## 4. Paradas y rollback

- **Freno**: `Ctrl+C` no viaja por AnyDesk → el freno real es cerrar la sesión o
  matar el proceso Python. El ledger permite reanudar sin repetir.
- **Fallo de red (Jev)**: `estado.py` devuelve `estado=None` con `error`, no
  "error de pantalla" → el bucle distingue "no pude clasificar" de "la pantalla está mal".
- **Fallo de Tesseract**: si el OCR no detecta cabecera, `tabla.ocr_tabla` cae a
  OCR plano (sin recorte) y marca `recortado: false` → se ve en el JSON.

---

## 5. Pendientes honestos (bloquean la puerta E1)

1. **Pegar en Chrome**: falta el contrato de columnas verificado y la mecánica
   de cambio de ventana (Alt+Tab / coordenadas) con verificación post-pegado.
2. **Calibración de la columna SUSCRIPTOR**: el fixture viene de un *zoom* de
   captura real; falta OCR directo de la pantalla real a 1:1 (la captura chica
   garblea los dígitos: `soBs7ss1` por `50867551`).
3. **Salto a unidades**: `Shift+F4` y `f16` sin verificar cuál entra. El
   clasificador ahora lo detecta (`cuenta_matriz` vs `formulario`), así que la
   prueba es de un clic.
4. **Jev**: la cuota free da 429. Hoy el gate real son las reglas; Jev queda
   como fallback y como criterio de segunda opinión.

---

## 6. Ponytail — qué NO se construyó (a propósito)

- No hay motor de estados genérico, ni cola, ni workers, ni plugin de visión.
- No hay retry/backoff: reintenta el bucle, no la red.
- No hay esquema JSON de validación: 4 estados y un dict bastan.
- Un archivo por capacidad. La lógica pura (`reglas`, `parse_row`, `parse_tabla`)
  vive separada de la E/S para poder testearla sin pantalla.
- `estado.py` hace OCR **local** y usa Jev solo si el texto es ambiguo: la
  velocidad no depende de un modelo.
