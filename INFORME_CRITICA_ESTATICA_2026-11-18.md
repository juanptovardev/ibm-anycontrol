# Informe de crítica estática — IBM AGENT

**Fecha:** 2026-11-18
**Alcance:** análisis estático y documental. No se ejecutó la suite, no se abrió el 5250, no se tocaron datos operativos.
**Objeto:** `C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT`
**Veredicto:** prototipo operativo con buen blindaje de flujo; **entrega no reproducible** y riesgos S1 de datos/seguridad. **NO-GO para producción**; GO para piloto controlado después de cerrar los P0.

---

## 0. Resumen ejecutivo

**Lo que está bien**
- El flujo B0–B7 está implementado con guardas reales: no teclea sin estado de formulario, verifica tinta antes de F10, aborta con estado inesperado, limita a 1 reintento y 2 recuperaciones, y marca `pegando` **antes** de tocar la hoja.
- El ledger es atómico (tmp + `os.replace`), hace upsert por id y distingue `ok`, `error`, `no_encontrado`, `requiere_revision`, `pegado_dudoso` y `pegando`.
- La ficha del edificio se guarda en el CSV **antes** de extraer, para no perderla si la extracción falla.
- La reanudación por página valida que la dirección del ledger coincida con la fila actual; si el id posicional quedó apuntando a otra dirección, empieza de cero.
- El tope de 40 páginas no se disimula: pasa a `requiere_revision`.
- `_jev` nunca levanta excepción y la clave no viaja en `argv` (usa un archivo temporal de `curl -K`).
- Hay 391 `def test_` en 46 archivos (conteo estático), buena intención de cobertura.

**Lo que bloquea**
1. La copia entregada no arranca tal cual: falta el venv hermano de `mcp-anydesk`, falta `config/jev.json` y no hay `.git`.
2. `_jev.py` manda texto OCR del 5250 (direcciones, suscriptores) a `opencode.ai`; si falta `config/jev.json`, usa la credencial personal de OpenCode del operador.
3. `direcciones.csv` se reescribe en sitio, sin tmp+replace: un corte a mitad de escritura puede truncar el maestro de 2168 filas.
4. La verificación de hoja es fail-open: si no hay captura o no hay texto, deja pasar el pegado.
5. El panel escucha en `0.0.0.0:8765`, con token de 32 bits, HTTP y endpoint de matar procesos.

**Lo que no se puede verificar con lo entregado**
- La corrida de 121 direcciones / 111 ok / 1710 filas.
- El conteo real de tests y los tiempos de 20,4 / 24–25 s por dirección.
- Los tags `v1.0`/`v1.1` de GitHub y los commits citados.

---

## 1. Método y límites

- Se leyeron 28 documentos (23.882 palabras) y los módulos de `tools/`.
- Se hicieron escaneos estáticos con Node: inventario, líneas, `def`, escrituras, locking, red, CSV, ledger, referencias.
- No se ejecutó `pytest`/`unittest`. El número 391 es un conteo de `def test_`, no un resultado de corrida.
- No se modificó ningún código, CSV, ledger ni configuración. El único archivo nuevo es este informe.

---

## 2. Fortalezas verificables

| # | Fortaleza | Evidencia |
|---|---|---|
| F1 | Macro determinista y reglas antes de Jev | `ADR-0001`, `ADR-0002`; `estado.py` `UMBRAL_JEV=0.6` |
| F2 | Guarda `pegando` antes del pegado | `loop.py:744-751` |
| F3 | Ledger atómico y upsert por id | `loop.py:184-228` |
| F4 | Ficha guardada antes de extraer | `loop.py:665-671` |
| F5 | Reanudación validada por dirección | `loop.py:889-910` |
| F6 | Tope de páginas explícito | `loop.py:828-834` (`MAX_PAGINAS=40`) |
| F7 | Credenciales 5250 fuera del código | `credenciales.py` (env → `~/.matriz/creds.json` → `config/creds.json`) |
| F8 | Jev no rompe el flujo | `_jev.py:47-92`; devuelve `ok=False`, nunca lanza |
| F9 | Clave fuera de `argv` | `_jev.py:72-78` (`curl -K` con archivo temporal) |
| F10 | Panel, traza y semáforo para observar | `ui.py`, `traza.py`, `docs/engineering/TRAZA_Y_SEMAFORO.md` |
| F11 | 391 tests estáticos en 46 archivos | Conteo `def test_` |

---

## 3. Hallazgos

### 3.1 S1 — Bloqueantes

#### F-01. La copia entregada no es ejecutable de punta a punta
- **Evidencia:** `arranca.bat:4` apunta a `..\mcp-anydesk\.venv\Scripts\python.exe`; `Test-Path` da `false`. `config/` está vacío: no hay `config/jev.json` ni `config/creds.json`. No hay `.git`.
- **Impacto:** el operador copia la carpeta a `Desktop\Proyectos\IBM AGENT`, ejecuta `arranca.bat` y falla antes de abrir el panel. Si lo corre desde `%USERPROFILE%\dev`, funciona solo si creó el venv hermano.
- **Agravante:** `arranca.bat` usa `--perfil=psicopata` por defecto; el propio README dice que ese perfil es “en la práctica imposible” (9,15 s/dir).
- **Fix:** preflight en `arranca.bat` con mensajes claros; incluir el venv o un `setup.ps1`; crear `config/jev.example.json` sin clave; cambiar el perfil por defecto a `rapido` o `humano`.

#### F-02. PII del 5250 enviada a un tercero
- **Evidencia:** `_jev.py:14` URL `https://opencode.ai/inference/systemone/v1/systemone`; `estado.py:343-346` envía `recorte[:2000]` cuando las reglas no deciden y `usar_jev=True`; `loop.py:247` usa Jev en la espera de estado. El texto OCR incluye direcciones y suscriptores.
- **Agravante:** `_jev.py:12` cae a `%USERPROFILE%\.local\share\opencode\auth.json`; en esta copia no existe `config/jev.json`, así que usaría la credencial personal del operador.
- **Impacto:** salida de datos internos sin DPA, sin consentimiento explícito y sin registro de qué se envió.
- **Fix (elegir una):**
  1. Deshabilitar Jev por defecto y exigir `MATRIZ_JEV_KEY` o `config/jev.json`.
  2. Eliminar el fallback a la credencial personal; solo credencial dedicada.
  3. Si se mantiene, enviar un texto sanitizado (sin direcciones/suscriptores) y documentar la base legal.

#### F-03. El maestro `direcciones.csv` se escribe sin atomicidad
- **Evidencia:** `matriz_ficha.escribe_ficha` abre `ruta` con `"w"` y reescribe las 2168 filas; `recepcion.escribe` usa `write_bytes` directo. No hay tmp+replace ni `.bak`.
- **Impacto:** un corte de luz, un cierre de Excel o un kill durante la escritura puede truncar el archivo que contiene las fichas. Es el dato más valioso del proyecto.
- **Contraste:** el ledger sí es atómico (`loop.py:184-228`) y `direcciones` sí usa tmp+replace en otras funciones; la inconsistencia es del escritor de fichas.
- **Fix:** un único escritor con `tmp` + `os.replace`, `.bak` rotativo y test de interrupción.

#### F-04. Verificación de hoja fail-open
- **Evidencia:** `hoja.py:49` devuelve `True, "sin captura: se deja pasar (fallo abierto)"`; solo devuelve `False` si leyó cabeceras y faltan o no están en la misma fila.
- **Impacto:** si el OCR no lee nada (pestaña equivocada, zoom, pantalla en blanco), el pegado sigue. `cp.G3` compara píxeles antes/después; si la hoja equivocada cambia, el diff puede dar “pegado”.
- **Fix:** identidad positiva de pestaña (título/URL), o fail-closed tras N lecturas vacías, o un marcador de corrida en la hoja.

#### F-05. Panel expuesto y token débil
- **Evidencia:** `ui.py:44` `secrets.token_hex(4)` = 32 bits; `ui.py:309` bind `0.0.0.0:8765`; token por `?k=` o header; `/api/matar` ejecuta `taskkill /T /F`; sin TLS ni rate limit; `arranca.bat` imprime el token y la URL.
- **Impacto:** en una red compartida, el panel queda al alcance de cualquiera; el token puede quedar en historial, screenshot o referrer.
- **Fix:** token de 128 bits, bind `127.0.0.1` por defecto, token solo por header, rate limit, POST con verificación de origen y confirmación para matar.

#### F-06. Secretos y PII en el árbol/repo
- **Evidencia:** `.gitignore` no incluye `config/jev.json` ni `datos/ui_token.txt`; sí incluye `direcciones.csv` (decisión del operador) y `ledger.csv` no está ignorado. `direcciones_problema.txt` y `direcciones_orden.csv` también contienen direcciones.
- **Impacto:** si el repo se comparte o se hace público por error, se filtran PII y, si existe, la clave de Jev. El README afirma que el repo es privado, pero no hay `.git` para verificarlo.
- **Fix:** `.gitignore` para `config/*.json`, `datos/ui_token.txt`, `direcciones_problema.txt`, `direcciones_orden.csv`; revisar visibilidad del repo; rotar cualquier clave que haya estado en disco compartido.

### 3.2 S2 — Altos

#### F-07. Dos contratos de entrada, uno muerto
- **Evidencia:** `loop.py:58` define `DATOS = .../datos.csv` y `lee_datos()` en `loop.py:123`; pero `loop.main` usa `lee_direcciones()` de `matriz_ficha` (`loop.py:919`). `datos/datos.csv` pesa 99 B y tiene una sola fila piloto (`PILOTO-01`, `CR 17B`, `175-77`), separada por comas y con LF; no es el insumo del runtime.
- **Impacto:** `RONDA_PRUEBAS.md`, `PROMPT_OBRERO_T-IBM-01.md` y `TRACE_FUNCIONES.md` siguen hablando de `datos.csv`; un operador o un test puede cargar el archivo equivocado.
- **Fix:** borrar `lee_datos`/`DATOS` o renombrarlos a `legacy`; actualizar docs y tests; dejar un solo contrato: `direcciones.csv` (3 columnas).

#### F-08. Dos escritores de `direcciones.csv` con encoding distinto
- **Evidencia:** `matriz_ficha` lee con `utf-8-sig` y escribe con BOM; `recepcion.escribe` escribe `;` en UTF-8 **sin BOM** y su docstring dice “siempre escribe con `,`” (falso: usa `SEP=";"`).
- **Impacto:** una pasada de recepción quita el BOM y puede romper acentos en Excel; la siguiente pasada de fichas lo repone. Dos fuentes de verdad para el mismo archivo.
- **Fix:** un solo módulo de escritura, un solo encoding, test de round-trip con acentos y `;`.

#### F-09. Sin lock de aplicación para el ledger
- **Evidencia:** no hay `msvcrt`, `filelock` ni `fcntl` en `tools/`. `supervisor.py:302-305` comprueba `supervisor.lock`, pero solo protege al supervisor. `loop.py` y `autonomo.py` pueden correr en paralelo y hacer read-modify-write del ledger completo.
- **Impacto:** pérdida de filas o estados pisados si dos procesos trabajan a la vez.
- **Fix:** lock con PID + timestamp + stale timeout; o un único writer. `supervisor.lock` debe detectar PID muerto, no exigir borrado manual.

#### F-10. Id posicional `D01…`
- **Evidencia:** `matriz_ficha.lee_direcciones` enumera filas y asigna `D%02d`; `escribe_ficha` usa `int(id)-1`. El GUIA ya lo marca como crítica.
- **Impacto:** si el operador ordena, filtra o inserta una fila, las fichas y el ledger quedan asociados a otra dirección. `reanuda_desde` mitiga el daño si la dirección no coincide, pero no impide el desalineamiento de fichas.
- **Fix:** clave estable (hash de dirección) o sidecar `id → dirección`; si se mantiene el id posicional, bloquear la edición del CSV mientras corre el agente.

#### F-11. La reanudación confía en el ledger, no en la hoja
- **Evidencia:** `reanuda_desde` lee `paginas_vistas` del ledger; no hay verificación de la última fila de la hoja ni marcador de corrida.
- **Impacto:** si alguien borra o edita filas de la hoja entre corridas, la reanudación duplica o salta páginas. El `pegando` cubre el corte del agente, no la edición externa.
- **Fix:** reconciliación pre-corrida (última fila / hash / marcador de run) o bloqueo de la hoja durante la corrida.

#### F-12. Once cifras distintas de tests
- **Evidencia:** 54 (ESTADO/EXECUTION), 56 (PROMPT_ARRANQUE), 105 (ESCALAMIENTO), 170 (MODULARIZACION), 186 y 199 (PLAN_0.2), 279 y 292 (PLAN_VERSION_FINAL), 345 (GUIA), 394 (README), 425 (HANDOFF). Conteo estático: 391 `def test_`.
- **Impacto:** no hay una fuente de verdad; no se puede saber si la suite pasa ni cuántos tests son reales.
- **Fix:** generar el número desde una corrida y publicarlo como artefacto; CI o `make verify`; badge en README.

#### F-13. `ui.matar` mata por nombre de comando
- **Evidencia:** `ui.py:66-71` busca `python.exe` cuyo `CommandLine` matchee `autonomo.py|loop.py|supervisor` y no `ui.py`, y ejecuta `taskkill /T /F`.
- **Impacto:** puede matar un `supervisor.py` de otro proyecto o un `loop.py` ajeno. No valida el directorio de trabajo ni el PID padre.
- **Fix:** filtrar por `ExecutablePath`/`CommandLine` con la ruta del proyecto, o guardar el PID del hijo y matar solo ese árbol.

#### F-14. Documentos y ADRs desactualizados
- **Evidencia:**
  - `ADR-0004` dice ledger append-only; el código hace upsert.
  - `docs/DISENO_FLUJO_DEFINITIVO.md` usa Alt+Tab; el código usa clic en taskbar.
  - `tools/README.md` repite append-only y Alt+Tab.
  - `TRACE_FUNCIONES.md` cita `tools/flow.py`, que no existe.
  - `README.md` dice que `config/jev.json` “ya contiene endpoint, modelo y clave”; no existe.
  - `PLAN_VERSION_FINAL` marca T2 “HECHO”; `MODULARIZACION.md` dice que no se ejecutó.
  - T5 “HECHO” pero “pendiente de medir en vivo”.
  - `ADR-0006` dice `%LOCALAPPDATA%`; `_jev.py:12` usa `%USERPROFILE%`.
  - `ESTADO_ORQUESTACION.md` no tiene entrada del 2026-11-03.
- **Impacto:** la gobernanza documental no permite reconstruir qué está hecho y qué no; un auditor no puede confiar en los estados.
- **Fix:** ADR de supersesión para 0004 y 0006; corregir DISEÑO/tools README/TRACE; una sola fuente de estado; archivar planes viejos.

### 3.3 S3 — Medios/bajos

| # | Hallazgo | Evidencia | Fix |
|---|---|---|---|
| F-15 | `direcciones_segunda.csv`: 7 direcciones duplicadas, 0 fichas | Stats CSV | Deduplicar con test |
| F-16 | 44 filas del ledger con rutas absolutas a `evidencia/` de otra máquina | `ledger.csv` | Rutas relativas + hash |
| F-17 | `direcciones_orden.csv` (135 filas) y `direcciones_problema.txt` en el árbol | `datos/` | Mover a `_local/` o borrar |
| F-18 | `datos/datos.csv` con 1 fila piloto, gitignored y citado por docs/tests | 99 B | Borrar o convertir en fixture |
| F-19 | `matriz_extraer.py` (14 líneas) y `orquesta.py` (32) son fachadas; `loop.py` sigue en 1036 líneas | Conteo | Terminar modularización o eliminar fachadas |
| F-20 | 28 .md / 23.882 palabras, planes solapados; 3 nombres del proyecto | Inventario | Consolidar en README + OPERATIONS + ARCHITECTURE; archivar |
| F-21 | `registrar_pegado.py` ajusta el ledger a mano sin validar la hoja | `tools/registrar_pegado.py` | Documentarlo o reemplazarlo por reconciliación |
| F-22 | `supervisor.lock` queda stale tras crash | `supervisor.py:302` | PID + stale timeout |
| F-23 | 128 archivos vs 126 documentados | Inventario | Actualizar el conteo |
| F-24 | `ui_token.txt` en texto plano, sin permisos restringidos | `ui.py:36-45` | Restringir ACL o usar env |

---

## 4. Validación documental

| Afirmación | Realidad estática | Estado |
|---|---|---|
| 121 direcciones, 111 ok, 10 no_encontrado, 134 páginas, 1710 filas | Ledger: 52 filas, 44 ok; no hay evidencia de esa corrida | No verificable |
| 394 tests (README) | 391 `def test_`; 11 cifras distintas en docs | Inconsistente |
| `config/jev.json` contiene endpoint, modelo y clave | `config/` vacío; `_jev` cae a la credencial personal | Falso |
| T2 modularización HECHA | `loop.py` 1036 líneas; fachadas de 14/32 líneas; `MODULARIZACION.md` sin ejecutar | Contradictorio |
| T5 HECHO (clic en taskbar) | Código con clic en taskbar; doc dice “pendiente medir en vivo” | Parcial |
| 20,4 s/dir | Plan final dice 24–25 s/dir; sin artefacto de medición | No verificable |
| Flujo con Alt+Tab | Código usa clic en icono de taskbar | Obsoleto |
| Ledger append-only | Upsert por id con `os.replace` | Obsoleto |
| 126 archivos | 128 archivos | Deriva menor |
| Repo GitHub `v1.0`/`v1.1` | No hay `.git`; el código cita `mcp-anydesk` v3.7.x | No verificable |
| Entrada `datos.csv` de 6 columnas | Runtime usa `direcciones.csv` de 3 columnas; `datos.csv` tiene 1 fila piloto | Contradictorio |
| “No usar Ctrl+C; pegar celda por celda” | Código usa Shift+clic y portapapeles | Prompt congelado obsoleto |
| Perfil `psicopata` por defecto | README dice que es imposible (9,15 s/dir) | Trampa operativa |
| `ADR-0006` ruta `%LOCALAPPDATA%` | `_jev.py` usa `%USERPROFILE%` | Inconsistente |
| Estado del 2026-11-03 | No hay entrada en `ESTADO_ORQUESTACION.md` | Hueco |

---

## 5. Flujo y contratos

### 5.1 B0–B7

| Regla | Implementación | Gap |
|---|---|---|
| B0 conexión | `espera_estado`, reconexión | Depende de AnyDesk free; cortes frecuentes |
| B1 no teclear sin formulario | `espera_estado` + `formulario` | Nada crítico |
| B2 verificar tinta antes de F10 | `hoja.verifica` | Fail-open si no hay OCR |
| B3 abortar estado inesperado | `procesa` devuelve `requiere_revision` | Nada crítico |
| B4 máximo 40 páginas | `MAX_PAGINAS=40` → `requiere_revision` | Correcto |
| B5 1 reintento, 2 recuperaciones | `REINTENTOS=1`, `MAX_RECUPERACION=2` | Correcto |
| B6 rastro en ledger + evidencia | `ledger_escribe`, `native_shot.save` | Evidencia no siempre presente |
| B7 no reprocesar `ok` | `pendientes` excluye terminales | Correcto |

### 5.2 P0–P5

| Paso | Implementación | Gap |
|---|---|---|
| P0 preflight | `estado`, `focus_guard` | Correcto |
| P1 buscar | `matriz_buscar` | Depende de OCR |
| P2 ficha | `recepcion.bloque_de` | Correcto |
| P3 extraer | `matriz_extraer` | Correcto |
| P4 pegar | `cp._copiar`, `_pegar_y_posicionar` | Sin verificación de contenido |
| P5 posicionar | `cp._pegar_y_posicionar` | Depende de la hoja externa |

### 5.3 Contratos

| Archivo | Formato real | Consumidor | Riesgo |
|---|---|---|---|
| `datos/direcciones.csv` | UTF-8 BOM, `;`, 3 columnas, 2168 filas, 206 fichas | `matriz_ficha.lee_direcciones` | Escritura no atómica; id posicional |
| `datos/ledger.csv` | UTF-8 BOM, `;`, 13 columnas, 52 filas | `loop.ledger_leido/escribe` | Sin lock; estados no validados |
| `datos/fichas_pendientes.csv` | 4 columnas, ficha con `\|` | `matriz_ficha.recupera_pendientes` | Correcto |
| `datos/traza.jsonl` | JSONL | Panel/auditoría | No inmutable |
| `datos/control.json` | JSON | Supervisor/loop | Correcto |
| `config/jev.json` | JSON con `url`/`key`/`model` | `_jev` | Ausente; secreto no ignorado |

### 5.4 Gaps de flujo, por orden de impacto

1. **Identidad de hoja**: no hay señal positiva de que la pestaña activa sea LIMPIEZA RR; el header es solo una heurística y falla abierto.
2. **Reconciliación externa**: el ledger no sabe si la hoja cambió entre corridas.
3. **Id estable**: el id posicional ata fichas y ledger al orden del CSV.
4. **Atomicidad**: el maestro se reescribe en sitio.
5. **PII/secretos**: Jev y el panel no tienen un límite claro de datos.
6. **Observabilidad**: hay traza y panel, pero no métricas por etapa ni alerta de atasco.

---

## 6. Plan priorizado

### P0 — antes de cualquier corrida real (1–2 días)

1. **Entrega reproducible (F-01):** preflight en `arranca.bat`, `setup.ps1`, `config/jev.example.json`, perfil por defecto realista.
2. **PII/Jev (F-02):** deshabilitar fallback personal; exigir credencial dedicada; o apagar Jev por defecto.
3. **Atomicidad del maestro (F-03):** tmp + `os.replace` + `.bak`; un solo escritor.
4. **Hoja fail-closed (F-04):** identidad de pestaña o bloqueo tras N lecturas vacías.
5. **Panel (F-05):** token de 128 bits, bind local por defecto, header-only, rate limit.
6. **Higiene de secretos (F-06):** `.gitignore`, rotación, revisión de visibilidad.

### P1 — antes de un piloto amplio (1–2 semanas)

7. **Contrato único de entrada (F-07/F-08):** borrar `datos.csv` y `lee_datos`; unificar encoding y escritor.
8. **Id estable (F-10):** hash o sidecar; bloquear edición del CSV durante la corrida.
9. **Reconciliación pre-corrida (F-11):** última fila / marcador de run.
10. **Lock de aplicación (F-09):** PID + stale; supervisor y loop comparten el lock.
11. **CI y conteo de tests (F-12):** `make verify`, artefacto de salida, badge.
12. **Kill acotado (F-13):** PID del hijo o ruta del proyecto.
13. **ADRs y docs (F-14):** supersesión de 0004/0006; corregir DISEÑO, tools README y TRACE.

### P2 — estructural (cuando haya volumen o varios operadores)

14. **Google Sheets API** o identidad positiva de hoja; elimina el pegado a ciegas.
15. **Modularización real (F-19):** separar percepción, política e I/O; o borrar fachadas.
16. **Esquemas tipados:** dataclasses/pydantic para ledger y filas; validación al leer.
17. **Observabilidad:** logs JSON, run_id, métricas por etapa, alerta de atasco.
18. **Calidad de datos (F-15):** deduplicar segunda; normalizar direcciones; reporte.
19. **Limpieza (F-16/F-17/F-18):** evidencia relativa, `_local/`, fixtures.
20. **Consolidación documental (F-20):** README + OPERATIONS + ARCHITECTURE + ADRs; archivar el resto.

---

## 7. Checklist go/no-go

| # | Check | Estado |
|---|---|---|
| G1 | Instalación reproducible en una máquina limpia | FAIL |
| G2 | Un solo contrato de entrada | FAIL |
| G3 | Maestro CSV atómico y con backup | FAIL |
| G4 | Política de PII/secretos explícita | FAIL |
| G5 | Panel seguro para LAN | FAIL |
| G6 | Identidad positiva de hoja | FAIL |
| G7 | Recuperación tras corte | PASS |
| G8 | Rastro auditorable | PARCIAL |
| G9 | Tests reproducibles y contados | FAIL |
| G10 | Docs y ADRs coherentes | FAIL |
| G11 | Rollback / historial | FAIL (no `.git`) |
| G12 | Calidad de datos de entrada | PARCIAL (7 duplicados, 206 fichas) |

**Veredicto:** NO-GO para producción. GO para un piloto controlado solo después de cerrar P0 (F-01 a F-06) y G1/G3/G4/G6.

---

## 8. Preguntas abiertas

1. ¿Jev es obligatorio? ¿Se acepta enviar direcciones/suscriptores a `opencode.ai`? ¿Hay DPA o consentimiento?
2. ¿El repo es privado? ¿Quién tiene acceso? ¿Se van a commitear `direcciones.csv` y `ledger.csv`?
3. ¿La hoja la edita solo el agente, o puede haber ediciones manuales entre corridas?
4. ¿El contrato definitivo es `direcciones.csv` de 3 columnas, o se van a agregar columnas?
5. ¿Se permite migrar a Google Sheets API o hay que mantener el pegado por GUI?
6. ¿Cuál es el volumen y la ventana reales (1180/día)?
7. ¿AnyDesk free es requisito o se puede usar licencia/otra vía?
8. ¿Quién aprueba los `requiere_revision` y con qué procedimiento?

---

## Anexo A. Métricas estáticas

| Métrica | Valor |
|---|---|
| Archivos / carpetas | 128 / 9 |
| Documentos `.md` | 28 |
| Palabras en docs | 23.882 |
| Archivos de test | 46 |
| `def test_` | 391 |
| `loop.py` | 1036 líneas |
| `direcciones.csv` | 2168 filas, 206 fichas (9,5 %) |
| `direcciones_segunda.csv` | 2167 filas, 7 duplicados, 0 fichas |
| `direcciones_orden.csv` | 135 filas |
| `ledger.csv` | 52 filas: 44 ok, 3 requiere_revision, 3 error, 2 no_encontrado |
| `datos.csv` | 99 B, 1 fila piloto (`PILOTO-01`) |
| `config/` | vacío |
| Venv hermano `mcp-anydesk` | ausente |
| `.git` | ausente |

## Anexo B. Verificaciones sugeridas (no ejecutadas)

```powershell
# Cuando se autorice una corrida de validación:
python -m pytest -q
python -m unittest discover -s tests -v
python tools/loop.py --dry --solo=D01
python tools/supervisor.py --max-vueltas=1 --horas=0.1
```

Antes de eso, el operador debería decidir si autoriza tests y una corrida real; este informe no lo hizo.
