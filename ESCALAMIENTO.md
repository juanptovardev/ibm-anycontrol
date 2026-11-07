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
| B8 | Una página **sin suscriptores** se salta: no se copia, no se pega | `click_sel.pagina_vacia` + `ciclo.extrae` | Vacía = 0 códigos en la columna Suscript + tinta verde < 40. Si hay tinta pero el OCR no ve códigos, se pregunta a Jev y solo se salta con conf ≥ 0.6 |

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

## 3. Rendimiento medido

Medido sobre la corrida real `run4` (27/10) y sobre las 34 capturas de
`evidencia/`. Antes de la versión definitiva: **~20 s por página**.

| Paso | Antes | Ahora | Cómo se midió |
|------|-------|-------|---------------|
| Foco MCP (9 llamadas/página) | 500 ms × 9 = 4,5 s | 50 ms × 9 = 0,45 s | `focus_and_verify` con la ventana ya delante (mcp-anydesk `2872044`) |
| OCR Tesseract (5 por página) | ~2,3 s × 5 = 12,5 s | ~2,2 s × 1 | `ocr_completo` (texto y words en una pasada) + reutilización de la captura de la página |
| Clasificación de la franja superior | pantalla completa | ~0,6 s | `clasificar_rapido` recorta 220 px (12/12 capturas correctas) |
| `changed_px` (diff de píxeles) | ~150 ms (bucle Python) | ~2 ms | `ImageChops.difference` en C |
| Recorrido completo de una página | ~20 s | **~6–8 s** | suma de lo anterior |

Por dirección (1 página): **~12–18 s**. Cada página extra del libro: +6–8 s.

El ciclo de 10 páginas del piloto (15:40:53 → 15:43:44) tardó 2 m 51 s con la
versión anterior; con la de hoy se estima en ~1 m 30 s.

---

## 4. Paradas y rollback

- **Freno**: `Ctrl+C` no viaja por AnyDesk → el freno real es cerrar la sesión o
  matar el proceso Python. El ledger permite reanudar sin repetir.
- **Fallo de red (Jev)**: `estado.py` devuelve `estado=None` con `error`, no
  "error de pantalla" → el bucle distingue "no pude clasificar" de "la pantalla está mal".
- **Fallo de Tesseract**: si el OCR no detecta cabecera, `tabla.ocr_tabla` cae a
  OCR plano (sin recorte) y marca `recortado: false` → se ve en el JSON.

---

## 5. Pendientes honestos

### Cerrado en la versión definitiva (27/10, T-IBM-04)

1. ~~Pegar en Chrome~~ → resuelto: la selección con **Shift+Clic** (mecánica
   aprobada por el operador) + `Alt+Tab` + `Ctrl+Shift+V`. Verificado en vivo:
   150 filas pegadas en 10 páginas.
2. ~~Retorno del listado al formulario~~ → resuelto: en `CONSULTA UNIDADES` la
   única tecla de la barra es `F12=Anterior`; con el teclado inhibido (`A X II`)
   `F3` no sale. La secuencia correcta es `Escape` + `F12` + `F12`.
3. ~~Salto a unidades~~ → resuelto: `F10` lleva a la **ficha del edificio** y
   `Shift+F4` al listado de unidades. El clasificador distingue los tres
   estados (`formulario` / `ficha` / `cuenta_matriz`).

### Sigue pendiente (bloquean la puerta E1)

4. **Contrato de columnas de la hoja**: verificado en vivo que los suscriptores
   caen en la columna J (`SUSCRIPTOR`) y la dirección en B; falta el mapa
   completo y confirmado por escrito.
5. **Calibración de la columna SUSCRIPTOR**: el fixture viene de un *zoom* de
   captura real; falta OCR directo de la pantalla real a 1:1 (la captura chica
   garblea los dígitos: `soBs7ss1` por `50867551`).
6. **Jev**: la cuota free da 429. Hoy el gate real son las reglas; Jev queda
   como fallback y como criterio de segunda opinión.
7. **Prueba en vivo de la versión definitiva**: el PC remoto se apagó a fin de
   día (corte de licencia de AnyDesk). Falta la corrida completa con las 5
   direcciones de `datos/direcciones.csv` y la medición del tiempo por página.

---

## 6. Causas de desconexión (dos, no una)

| Síntoma en pantalla | Estado | Acción |
|--------------------|--------|--------|
| "Conexión finalizada … limitación de la licencia" | `desconectado` | El botón **Repetir** es local: `tools/vigia.py <hwnd> --repetir` lo pulsa y reconecta (10–30 s) |
| "No se puede acceder al ordenador / este puesto de trabajo" | `desconectado` | El AnyDesk del PC remoto está apagado: no hay nada que reconectar |

Tesseract lee la 'o' acentuada como '6' ("conexi6n", "limitaci6n"), así que
las regex aceptan ambas formas y el corte se detecta **por regla**, sin gastar
una llamada a Jev.

---

## 7. Ponytail — qué NO se construyó (a propósito)

- No hay motor de estados genérico, ni cola, ni workers, ni plugin de visión.
- No hay retry/backoff: reintenta el bucle, no la red.
- No hay esquema JSON de validación: 4 estados y un dict bastan.
- Un archivo por capacidad. La lógica pura (`reglas`, `parse_row`, `parse_tabla`)
  vive separada de la E/S para poder testearla sin pantalla.
- `estado.py` hace OCR **local** y usa Jev solo si el texto es ambiguo: la
  velocidad no depende de un modelo.
