# CHECKLIST DE FINIQUITO — IBM AGENT

**Proyecto:** IBM AnyControl / `ibm-anycontrol`
**Plan:** `FINIQUITO/PLAN_DE_FINIQUITO.md`
**Informe base:** `INFORME_CRITICA_ESTATICA_2026-11-18.md`
**EF:** ______________________
**Operador:** __________________
**Revisor ciego:** _____________
**Fecha de inicio:** ___________
**Baseline (ZIP + hash):** `C:\Backups\IBM-AGENT\IBM-AGENT-20261118-133911.zip` · `26ECF02FE9D97E4962AD8889FF20F984EF293D311BDE663D1328EC399F4310EA` · manifiesto `manifest-20261118-133911.csv` (132 filas)

**Leyenda:** `[ ]` pendiente · `[x]` hecho con evidencia · `[!]` bloqueado · `[-]` waiver firmado.

**Regla:** no se marca `[x]` sin output pegado en `FINIQUITO/evidencia/<WP>/`.

---

## 0. Autorización y congelamiento

- [x] 0.1 — El operador autorizó ejecutar WP-00 (“dale”, 2026-11-18).
  - Evidencia: mensaje del operador; el alcance completo (D-01..D-07) sigue pendiente.
- [!] 0.2 — Ventana de trabajo no formalizada; WP-00 se ejecutó 13:36–13:39 sin corridas reales.
  - Evidencia: `evidencia/WP-00/wp00-20261118-133911.log`.
- [x] 0.3 — Excel cerrado; agentes detenidos; AnyDesk abierto (15316/15540/15668), no escribe en el proyecto.
  - Evidencia: log WP-00, sección “Procesos”.
- [x] 0.4 — Datos reales respaldados; correcciones todavía no autorizadas.
  - Evidencia: WP-00.
- [ ] 0.5 — Revisor ciego designado (no implementó).
  - Nombre: ______________________

---

## G0 — Baseline y restore

- [x] G0-01 — ZIP del proyecto creado.
  - Evidencia: `C:\Backups\IBM-AGENT\IBM-AGENT-20261118-133911.zip` (337.331 B, 132 entradas).
  - Log: `evidencia/WP-00/wp00-20261118-133911.log`.
  - Nota: el ZIP `133642` se descartó; se generó antes de corregir el informe.
- [x] G0-02 — Manifiesto SHA256 completo.
  - Evidencia: `C:\Backups\IBM-AGENT\manifest-20261118-133911.csv` (132 filas).
  - SHA256 del manifiesto: `8997CA7C7F0D1C36BA3E29718493FC9ED340F7D22D11E4C2AEBE15155385EAAD`.
- [x] G0-03 — Hashes de archivos críticos.
  - Evidencia: `evidencia/WP-00/hashes-20261118-133911.txt` (4/4).
  - Direcciones `E1045E...227E`; ledger `76044A...5861`; segunda `255520...CE6C`; datos `299973...40F0`.
- [x] G0-04 — Restore en carpeta temporal.
  - Evidencia: `C:\Users\JUANP_~1\AppData\Local\Temp\IBM-AGENT-restore-20261118-133911` (132 archivos).
- [x] G0-05 — Hashes del restore coinciden con el original.
  - Resultado: 4/4 `True` (direcciones, ledger, segunda, datos).
- [x] G0-06 — Conteos del restore.
  - Resultado: 2168 direcciones / 206 fichas / 52 ledger / 2167 segunda / 1 datos.
- [-] G0-07 — (Opcional) Git local sin remoto.
  - No ejecutado: decisión D-04 pendiente; el ZIP es el baseline completo.
- [x] G0-08 — Operador confirma “baseline congelado”.
  - Evidencia: mensaje “daleeee” (2026-11-18), autorización para ejecutar WP-01.

**Salida G0:** backup restaurado + hashes iguales + autorización escrita. Sin esto, no se toca código.

---

## G1 — P0

### WP-01 — Preflight de entrega

- [x] G1-01 — `setup.ps1 -Check` existe y valida Python, venv, config, CSV y compileall.
  - Incluye avisos de imports, Tesseract, Jev y AnyDesk; `-Install` opcional.
- [x] G1-02 — En copia sin venv: exit 2 y mensaje accionable.
  - Comando: `powershell -ExecutionPolicy Bypass -File setup.ps1 -Check`
  - Resultado: `REAL_EXIT=2`; “Falta ..\mcp-anydesk\.venv\Scripts\python.exe...”.
  - Evidencia: `evidencia/WP-01/preflight-fail.txt`.
- [x] G1-03 — En copia buena: exit 0.
  - Resultado: `FIXTURE_EXIT=0`; `preflight OK`; avisos esperados por venv vacío.
  - Evidencia: `evidencia/WP-01/preflight-ok.txt`.
- [x] G1-04 — `arranca.bat` no arranca si el preflight falla; default `humano` (o `rapido`).
  - Resultado: `BAT_EXIT=2`, “Preflight fallo...”, no arrancó el panel.
  - Evidencia: `evidencia/WP-01/arranca-fail.txt`.
- [x] G1-05 — `config/jev.example.json` existe sin clave real.
  - Contenido: `url`, `model`, `key: ""`.
- [x] G1-06 — README corregido: config no viene con clave.
  - También default `humano`.

### WP-02 — PII/Jev

- [x] G1-07 — Sin clave, `disponible()` es `False`.
  - Comando: `python -c "import sys; sys.path.insert(0, 'tools'); import _jev; print(_jev.disponible())"`
  - Resultado: `False` sin env/config; `False` con `MATRIZ_JEV=1` sin key; `False` con `MATRIZ_JEV=0` + key.
  - Evidencia: `FINIQUITO/evidencia/WP-02/checks.txt`.
- [x] G1-08 — `MATRIZ_JEV=0` no llama a `ask` (test unitario).
  - Resultado: `test_jev_apagado_no_llama` y `test_jev_apagado_no_llama_ask` OK; 51/51 tests.
- [x] G1-09 — Sin fallback a `%USERPROFILE%\...\auth.json`.
  - Comando: `Select-String -Path tools\_jev.py -Pattern "USERPROFILE|auth\.json"`
  - Resultado: 0 matches; `config/jev.json` no existe en el baseline.
- [x] G1-10 — `docs/PRIVACY.md` describe qué se envía y cómo apagarlo.
  - Resultado: creado con alcance, destino, retención, apagado/encendido y responsables.
- [x] G1-11 — Operador aprobó Jev on/off (D-01).
  - Resultado: D-01 = **OFF por defecto**, registrada en `FINIQUITO/DECISIONES_OPERADOR.md`.

### WP-03 — CSV atómico

- [x] G1-12 — `csvio.write_atomic` con tmp + fsync + `.bak` + `os.replace`.
  - Resultado: temporal único en el mismo directorio, `flush` + `os.fsync`, `.bak` y `os.replace`; el temporal se limpia si falla.
- [x] G1-13 — `escribe_ficha` y `recepcion.escribe` usan el helper.
  - Resultado: ambos delegan en `csvio.escribe_direcciones` / `csvio.write_atomic`.
- [x] G1-14 — Test de fallo inyectado: hash original intacto; sin `.tmp`.
  - Comando: `python -m unittest tests.test_csvio tests.test_escribe_ficha_bloqueado -v`
  - Resultado: 7 tests OK; el original queda intacto y no quedan `*.tmp`.
- [x] G1-15 — Round-trip: 2168 filas, 206 fichas, BOM, `;`, acentos.
  - Resultado: `test_round_trip_2168_filas_206_fichas` OK; BOM, `;`, ÑANDÚ y multilínea conservados.
- [x] G1-16 — Sin escrituras directas en los dos módulos.
  - Comando: `Select-String -Path tools\matriz_ficha.py,tools\recepcion.py -Pattern "write_bytes|open\(.*[\"']w[\"']"`
  - Resultado: 1 coincidencia, `matriz_ficha.py:143`, y es `fichas_pendientes.csv` (respaldo), no `direcciones.csv`. El maestro solo se escribe por `csvio`.

### WP-04 — Hoja fail-closed

- [x] G1-17 — `hoja.identidad()` exige título/URL + cabeceras.
  - Evidencia: `checks.txt` (`def identidad`; `hoja.identidad` en `cp.py`).
- [x] G1-18 — Sin captura/texto → `False` por defecto.
  - Evidencia: tests `test_sin_captura_bloquea`, `test_ocr_vacio_bloquea`.
- [x] G1-19 — `cp` no pega si `identidad()` es `False`; marca `requiere_revision`.
  - Evidencia: `test_identidad_false_no_pega`; `cp.py:268` emite `Halt` con “requiere revision”; el guard `pegando` del ledger lo convierte en `requiere_revision`.
- [x] G1-20 — Tests: `None` → False; título incorrecto → False; correcto → True.
  - Comando: `python -m unittest tests.test_hoja tests.test_cp -v`; **22/22 OK**.
- [!] G1-21 — Dry-run simulado con hoja equivocada no pega; dry-run real pendiente en Gate 3.
  - Evidencia: `evidencia/WP-04/dry-wrong-tab.txt` (mock; no toca la hoja real).
- [x] G1-22 — `HOJA_FAIL_OPEN` default 0; `=1` solo escape heredado.

### WP-05 — Panel

- [x] G1-23 — Token >=22 caracteres; rota el viejo. Evidencia: `WP-05/tests-wp05.out.txt` (17/17).
- [x] G1-24 — Bind default `127.0.0.1`. Evidencia: `WP-05/http.txt` (`127.0.0.1:8799`).
  - Comando: `Get-NetTCPConnection -LocalPort 8765 | Select-Object LocalAddress`
- [x] G1-25 — Sin token → 401; con token → 200. Evidencia: `WP-05/http.txt`.
- [x] G1-26 — 21 requests/min → 429. Evidencia: `WP-05/http.txt` (primer 429 en req13; 8 previas + 13 = 21).
- [x] G1-27 — `/api/matar` solo POST + `confirm=1`; sin confirm → 400 y no mata. Evidencia: `WP-05/http.txt`.
- [x] G1-28 — `ui_token.txt` con ACL solo del usuario actual. Evidencia: `WP-05/http.txt` (`icacls`: solo `JUANPC\juanp_8h8f07l:(F)`).
- [x] G1-29 — `arranca.bat` no imprime el token. Evidencia: `WP-05/checks.txt` (`type datos\ui_token.txt` = 0).

### WP-06 — Higiene

- [x] G1-30 — `.gitignore` cubre `config/*.json`, `ui_token.txt`, `direcciones_problema.txt`, `direcciones_orden.csv`, `evidencia/`, `traza`, `control`, `lock`, `fichas_pendientes`.
- [x] G1-31 — `scripts/check_secrets.ps1` exit 0 en árbol limpio.
- [x] G1-32 — Prueba negativa: secreto falso → exit 1.
- [!] G1-33 — Claves rotadas si estuvieron expuestas.
- [!] G1-34 — Operador aprobó política de datos (D-02).

**Salida G1:** S1 = 0; WP-01..06 con evidencia; D-01/D-02 aprobadas.

---

## G2 — Integridad y operación

### WP-07 — Contrato único de entrada

- [x] G2-01 — `DATOS`, `lee_datos` y `datos.csv` eliminados o marcados legacy.
- [x] G2-02 — `grep` en `tools/` y `tests/` sin `datos.csv`.
  - Comando: `Select-String -Path tools\*.py,tests\*.py -Pattern "datos\.csv|lee_datos|DATOS\s*="`
  - Esperado: 0 (salvo legacy documentado).
- [x] G2-03 — Test de contrato: 3 columnas, `D01`, acentos.
- [!] G2-04 — Docs `RONDA`, `PROMPT_OBRERO`, `TRACE` actualizados.

### WP-08 — Id estable

- [x] G2-05 — `datos/ids.csv` con `id,parte1,parte2,hash`.
- [x] G2-06 — `escribe_ficha` busca por hash, no por `int(id)-1`.
- [x] G2-07 — Test: reordenar CSV no cambia el id de la misma dirección.
  - Comando: `python -m pytest tests/test_ids.py -q`
- [x] G2-08 — Si no hay sidecar, lock de edición documentado.

### WP-09 — Reconciliación

- [ ] G2-09 — `datos/run.json` con `run_id`, inicio, sheet, última fila.
- [ ] G2-10 — Si la hoja no coincide, aborta antes de pegar.
- [ ] G2-11 — Dry-run con fila extra simulada: `requiere_revision`, sin pegado.

### WP-10 — Lock

- [ ] G2-12 — `tools/lock.py` con PID + liveness.
- [ ] G2-13 — `loop`, `autonomo` y `supervisor` usan el lock.
- [ ] G2-14 — Dos procesos: el segundo exit 2.
- [ ] G2-15 — Lock stale se limpia; heartbeat documentado.

### WP-11 — Runner y conteo

- [ ] G2-16 — `scripts/verify.ps1` corre compileall + suite.
- [ ] G2-17 — Artefacto JSON con total/passed/failed/skipped.
- [ ] G2-18 — `tools/verifications/test_count.txt` generado.
- [ ] G2-19 — README y docs usan ese número, no uno escrito a mano.

### WP-12 — Kill acotado

- [ ] G2-20 — `datos/workers.json` registra PID del proyecto.
- [ ] G2-21 — `/api/matar` mata solo esos PID.
- [ ] G2-22 — Decoy `supervisor.py` en otra carpeta sobrevive.
- [ ] G2-23 — Lock stale se limpia sin borrar a mano.

### WP-13 — Docs y ADRs

- [ ] G2-24 — ADR-0007 (ledger upsert) creado.
- [ ] G2-25 — ADR-0008 (Jev/PII) creado como **Propuesto**; decisión D-01 registrada.
- [ ] G2-26 — ADR-0004 con banner “Superado por ADR-0007”; ADR-0006 con aviso a ADR-0008 (Propuesto), sin marcar superado hasta D-01.
- [ ] G2-27 — `DISENO` y `tools/README` con taskbar, no Alt+Tab.
- [ ] G2-28 — `TRACE` sin `flow.py`.
- [ ] G2-29 — README con conteo real, config example, 128 archivos, perfil `rapido`.
- [ ] G2-30 — `PLAN_VERSION_FINAL` con T2/T5/corrida corregidos.
- [ ] G2-31 — `GUIA` con tests/tiempo reales y nota fail-open.
- [ ] G2-32 — `RONDA`/`PROMPT_OBRERO` con `direcciones.csv` y portapapeles.
- [ ] G2-33 — `ESCALAMIENTO` con upsert y tests reales.
- [ ] G2-34 — Nombre canónico elegido y aplicado.
- [ ] G2-35 — `ESTADO_ORQUESTACION` con entrada 2026-11-18.
- [ ] G2-36 — Planes viejos archivados en `docs/archive/`.
- [ ] G2-37 — Grep de cierre sin claims falsos.
  - Comando: `Select-String -Path README.md,docs\*.md,tools\README.md -Pattern "394 tests|345 tests|append-only|Alt\+Tab|flow\.py|config/jev\.json ya"`
  - Esperado: 0 (o solo `docs/archive/`).

**Salida G2:** P1 cerrado o waiver; suite verde; docs coherentes.

---

## G3 — Auditoría y release

- [ ] G3-01 — `scripts/verify.ps1` completa, exit 0.
- [ ] G3-02 — Dry-run autorizado (`--dry --solo D01`) con log.
- [ ] G3-03 — Restore del backup y hashes críticos iguales.
- [ ] G3-04 — Dossier completo con evidencia real.
- [ ] G3-05 — Revisor ciego re-ejecutó 3 acceptance (WP-03, WP-04, WP-05).
- [ ] G3-06 — Veredicto firmado: CERRADO / CERRADO CON RESERVAS / RECHAZADO.
- [ ] G3-07 — Release candidate: tag `v1.0.0-finiquito` o ZIP + SHA256.
- [ ] G3-08 — `README_OPERACION.md` entregado (arranque, parada, panel, recuperación, límites).
- [ ] G3-09 — Dossier y evidencia archivados en `FINIQUITO/evidencia/`.
- [ ] G3-10 — Operador acepta el release por escrito.

---

## Tabla de waivers

| Riesgo | Motivo | Vigencia | Mitigación | Aprobado por | Fecha |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |

**Regla:** ningún waiver para S1. Ningún waiver para “no hice backup”.

---

## Firma final

| Rol | Nombre | Fecha | Firma |
|---|---|---|---|
| Encargado de Finiquito | | | |
| Revisor ciego | | | |
| Operador | | | |

**Resultado:** `[ ] CERRADO` · `[ ] CERRADO CON RESERVAS` · `[ ] RECHAZADO`

**Reservas / notas:**

____________________________________________________________________________
