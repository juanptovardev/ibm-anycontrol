# PLAN DE FINIQUITO — IBM AGENT

**Versión:** 1.0
**Fecha:** 2026-11-18
**Entrada:** `INFORME_CRITICA_ESTATICA_2026-11-18.md`
**Estado:** listo para ejecutar. Requiere aprobación del operador para el Gate 0 y para cada decisión marcada como SOLO-HUMANO.

---

## 0. Cómo se usa este plan

1. El Encargado de Finiquito (EF) lee completo este plan y el informe de crítica antes de tocar nada.
2. Ejecuta **WP-00** (baseline + backup + restore). Sin WP-00 no hay ningún otro WP.
3. Ejecuta un WP por vez. No abre el siguiente sin dossier y aceptación del anterior.
4. Pega output real de cada comando. No se aceptan adjetivos ("funciona", "anda", "quedó bien").
5. Si un WP falla dos veces: STOP y escala. No improvisa.
6. Las decisiones de negocio, PII, credenciales y release las aprueba el operador. El EF propone y ejecuta; no decide esas materias.

**Regla de evidencia:** todo criterio de aceptación se re-ejecuta desde cero al cerrar el Gate. Un claim sin output no cuenta.

---

## 1. Mandato del Encargado de Finiquito

### 1.1 Misión

Llevar el proyecto de "prototipo operativo con documentación dispersa" a **entrega reproducible, auditable y operable**, sin ampliar el alcance funcional.

El finiquito no es "agregar features". Es:

- cerrar los riesgos S1/P0;
- dejar una sola verdad documental;
- probar que el backup se restaura;
- dejar el número real de tests y una corrida reproducible;
- entregar dossier, manual de operación y rollback.

### 1.2 Autoridad

El EF puede:

- crear un worktree/rama o un snapshot por WP;
- editar código, tests y documentación dentro del alcance del WP;
- ejecutar tests, `compileall`, dry-runs y simulaciones;
- crear backups y manifiestos de hash;
- proponer ADRs y correcciones documentales;
- rechazar un WP sin evidencia.

El EF **no puede**:

- tocar datos reales (`direcciones.csv`, `ledger.csv`) sin backup verificado y autorización escrita;
- cambiar el alcance funcional, el contrato de 3 columnas ni las reglas de negocio;
- aceptar su propio trabajo como cierre final;
- hacer push a un remoto, publicar el repo o crear un release público;
- comprar, contratar o usar credenciales nuevas sin aprobación;
- borrar evidencia, ledger o backups.

### 1.3 Roles

| Rol | Quién | Responsabilidad |
|---|---|---|
| Operador | Dueño del proceso | Aprueba P0, política PII, ventana de corrida y release. |
| EF | Encargado de finiquito | Ejecuta WPs, produce evidencia y dossier. |
| Revisor ciego | Persona que no implementó | Re-ejecuta acceptance y firma veredicto. |
| Auditor | Opcional / externo | Revisa seguridad, datos y consistencia documental. |

Si el EF es la misma persona que escribió el código, el **revisor ciego es obligatorio**.

### 1.4 Reglas de oro

1. Un WP = un cambio acotado = un snapshot/commit.
2. Aceptación = comando + output esperado, nunca adjetivo.
3. Nadie califica su propio trabajo.
4. Sin dossier no hay cierre.
5. Erratas y correcciones van en el WP, no en un "arreglo después".
6. STOP + escalar, no improvisar.
7. La regla del 80% aplica: si el repo ya resuelve algo, se reutiliza; no se reescribe.

---

## 2. Definición de finiquito (DoD)

El proyecto se considera finiquitado solo si **todas** se cumplen:

- [ ] 0 hallazgos S1 abiertos.
- [ ] P0 (WP-01..WP-06) cerrados al 100 %, con evidencia re-ejecutada.
- [ ] P1 (WP-07..WP-13) cerrados o con waiver firmado (máximo 3, nunca S1).
- [ ] Suite completa verde en una sola corrida; artefacto con conteo real de tests.
- [ ] Backup ZIP + manifiesto SHA256 + restore probado en carpeta temporal.
- [ ] `direcciones.csv` conserva 2168 filas y 206 fichas; hash antes/después documentado.
- [ ] Política PII/Jev aprobada por el operador; sin credenciales personales en el flujo.
- [ ] Panel seguro por defecto: localhost, token fuerte, sin endpoint destructivo abierto.
- [ ] Hoja fail-closed: pestaña equivocada o sin lectura → no pega.
- [ ] Documentación coherente: sin claims falsos sobre tests, config, perfiles, Alt+Tab ni append-only.
- [ ] ADR-0007 (ledger upsert) creado; ADR-0008 (Jev/PII) como **Propuesto** y aprobado por el operador (D-01); ADR-0004 marcado como superado y ADR-0006 con aviso a ADR-0008 hasta D-01.
- [ ] Dossier de cierre aprobado por revisor ciego.
- [ ] Release candidate + manual de operación + rollback entregados.

---

## 3. Gates y secuencia

| Gate | Objetivo | WPs | Criterio de salida |
|---|---|---|---|
| G0 | Baseline y seguridad | WP-00 | Backup restaurado y hashes coinciden. |
| G1 | Cerrar P0 | WP-01..WP-06 | S1 = 0; acceptance verde; operador aprueba PII y panel. |
| G2 | Integridad y operación | WP-07..WP-13 | P1 cerrado o waiver; suite verde; docs coherentes. |
| G3 | Auditoría y release | Cierre | Dossier aprobado; release candidate firmado. |

**Estimación base:** G0 0,5 día; G1 2–3 días; G2 5–8 días; G3 1–2 días. Total 9–14 días de un dev que conoce el código. Si el EF no lo escribió, multiplicar por 1,5.

---

## 4. Gate 0 — Baseline y seguridad

### WP-00 — Congelar el estado y probar restore

**Objetivo:** tener un punto de retorno verificable antes de cualquier cambio.

**Por qué:** el proyecto no es git. Sin snapshot + hash + restore, cualquier corrección es irreversible y no auditable.

**Alcance permitido:** crear carpeta de backups y manifiestos fuera del árbol operativo; no editar código ni datos.

**Prohibido:** ejecutar `loop.py`, `supervisor.py`, `autonomo.py`, tests o cualquier cosa que escriba en `datos/` durante el snapshot.

**Pasos:**

1. Pedir al operador que cierre Excel, AnyDesk y cualquier agente en curso.
2. Crear carpeta de backups fuera de OneDrive (o en una carpeta local cifrada):
   ```powershell
   $root = "C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT"
   $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
   $backupDir = "C:\Backups\IBM-AGENT"
   New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
   ```
3. Crear ZIP del proyecto completo:
   ```powershell
   $zip = Join-Path $backupDir "IBM-AGENT-$stamp.zip"
   Compress-Archive -Path "$root\*" -DestinationPath $zip -CompressionLevel Optimal
   ```
4. Generar manifiesto SHA256 de todos los archivos:
   ```powershell
   Get-ChildItem -Path $root -Recurse -File |
     ForEach-Object { Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256 } |
     Select-Object Hash, Path |
     Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $backupDir "manifest-$stamp.csv")
   ```
5. Generar hashes de los archivos críticos:
   ```powershell
   Get-FileHash "$root\datos\direcciones.csv", "$root\datos\ledger.csv", "$root\datos\direcciones_segunda.csv", "$root\datos\datos.csv" -Algorithm SHA256 |
     Format-Table -AutoSize
   ```
6. Probar restore en carpeta temporal:
   ```powershell
   $tmp = Join-Path $env:TEMP "restore-ibm-$stamp"
   Expand-Archive -Path $zip -DestinationPath $tmp -Force
   Get-FileHash "$tmp\datos\direcciones.csv", "$tmp\datos\ledger.csv" -Algorithm SHA256
   ```
7. Verificar conteos en el restore:
   ```powershell
   (Import-Csv "$tmp\datos\direcciones.csv" -Delimiter ";").Count   # esperado 2168
   (Import-Csv "$tmp\datos\ledger.csv" -Delimiter ";").Count        # esperado 52
   (Import-Csv "$tmp\datos\direcciones_segunda.csv" -Delimiter ";").Count # esperado 2167
   ```
8. (Opcional) Inicializar git local **solo después** del backup, sin remoto:
   ```powershell
   git init
   # NO ejecutar `git add -A` todavía: el .gitignore se corrige en WP-06.
   git add README.md arranca.bat tools docs tests FINIQUITO
   git commit -m "baseline: codigo y docs congelados 2026-11-18"
   ```
   No agregar `datos/` ni `config/` hasta completar WP-06. El baseline completo
   (incluidos datos y config) ya está en el ZIP con hash; git es solo para diffs
   de código. Si el operador no quiere git, usar un snapshot ZIP por WP.

**Aceptación:**

- El ZIP existe y contiene al menos 128 archivos.
- El manifiesto tiene una fila por archivo (>= 128).
- Los hashes del restore coinciden con los del original.
- Los conteos del restore son 2168 / 52 / 2167.
- El operador confirma por escrito: "baseline congelado, autorizo correcciones".

**Evidencia:** `FINIQUITO/evidencia/WP-00/` con `backup.txt`, `manifest.csv`, `hashes.txt`, `restore.txt`.

**Rollback:** restaurar el ZIP completo en una carpeta limpia; comparar hashes.

**Estimación:** 2–3 h.

---

## 5. Gate 1 — Cerrar P0

### WP-01 — Preflight de entrega ejecutable

**Objetivo:** que una copia limpia falle con un mensaje claro o arranque; nunca que falle a mitad de una corrida.

**Por qué:** hoy `arranca.bat` apunta a un venv que no existe, `config/` está vacío y el perfil por defecto es `psicopata`.

**Alcance permitido:** `arranca.bat`, `setup.ps1` (nuevo), `config/jev.example.json` (nuevo), `README.md`.

**Prohibido:** descargar dependencias sin aprobación; crear credenciales; cambiar el flujo funcional.

**Pasos:**

1. Crear `setup.ps1 -Check` que valide:
   - `python --version` >= 3.11;
   - `..\mcp-anydesk\.venv\Scripts\python.exe` existe;
   - `config\jev.json` o `MATRIZ_JEV_KEY` (si no, avisar y dejar Jev off);
   - `datos\direcciones.csv` existe y tiene 3 columnas;
   - `python -m compileall -q tools` sale 0;
   - el runner de tests está disponible.
2. `setup.ps1 -Install` opcional (solo con aprobación): crear venv, `pip install -r requirements.txt` si existe, y copiar `config\jev.example.json` a `config\jev.json` sin clave.
3. `arranca.bat` llama a `setup.ps1 -Check`; si falla, imprime el motivo y `exit /b 2`.
4. Cambiar el perfil por defecto a `rapido` (o `humano`); `psicopata` solo con `--perfil=psicopata` explícito y aviso.
5. `config/jev.example.json` con placeholders; nunca una clave real.
6. README: reemplazar "config/jev.json ya contiene la clave" por "crear desde el example o definir MATRIZ_JEV_KEY".

**Aceptación:**

```powershell
# En una copia sin ..\mcp-anydesk\.venv:
powershell -ExecutionPolicy Bypass -File setup.ps1 -Check
# Esperado: exit 2 y mensaje "Falta ..\mcp-anydesk\.venv..."

# En la copia buena:
powershell -ExecutionPolicy Bypass -File setup.ps1 -Check
# Esperado: exit 0 y "preflight OK"
```

- `arranca.bat` no arranca el panel si el preflight falla.
- `Select-String -Path arranca.bat -Pattern "psicopata"` no aparece como default.

**Evidencia:** `evidencia/WP-01/preflight-fail.txt`, `preflight-ok.txt`.

**Rollback:** restaurar `arranca.bat` del baseline; borrar `setup.ps1` y `config/jev.example.json`.

**Estimación:** 4 h.

---

### WP-02 — PII y Jev: apagado por defecto o clave dedicada

**Objetivo:** que el OCR de direcciones/suscriptores no salga a un tercero sin decisión explícita.

**Por qué:** `estado.py:343-346` envía `recorte[:2000]` a `opencode.ai`; `_jev.py:12` usa la credencial personal de OpenCode si falta configuración.

**Alcance permitido:** `tools/_jev.py`, `tools/estado.py`, `tools/loop.py`, `config/jev.example.json`, `docs/PRIVACY.md` (nuevo), `README.md`.

**Prohibido:** usar la credencial personal como fallback; enviar PII sin opt-in; cambiar el modelo sin aprobación.

**Pasos:**

1. Eliminar el fallback a `%USERPROFILE%\.local\share\opencode\auth.json`.
2. `disponible()` devuelve `False` si no hay `MATRIZ_JEV_KEY` o `config/jev.json` con clave.
3. `MATRIZ_JEV` con default `0` (apagado). `MATRIZ_JEV=1` activa.
4. `estado.clasificar_texto` y `loop` respetan `usar_jev` y `disponible()`.
5. Log de arranque: `jev=off (sin clave dedicada)` o `jev=on (clave dedicada)`.
6. `docs/PRIVACY.md`: qué se envía (primeros 2000 caracteres del OCR), a qué endpoint, retención, base legal y cómo apagarlo.
7. Si el operador elige Jev on: clave dedicada, no personal; documentar el DPA/acuerdo.

**Aceptación:**

```powershell
python -c "from tools._jev import disponible; print(disponible())"
# Sin clave: False. Con MATRIZ_JEV=0: False.

Select-String -Path tools\_jev.py -Pattern "USERPROFILE|auth\.json"
# Esperado: 0 matches.
```

- Test unitario con monkeypatch: con `MATRIZ_JEV=0`, `estado.clasificar_texto` no llama a `_jev.ask`.
- `docs/PRIVACY.md` existe y describe el envío.

**Evidencia:** `evidencia/WP-02/jev-off.txt`, `privacy.md`, test output.

**Rollback:** restaurar `_jev.py`, `estado.py`, `loop.py`; dejar Jev como estaba solo si el operador lo autoriza.

**Estimación:** 4 h.

---

### WP-03 — Escritura atómica del maestro CSV

**Objetivo:** que un corte de luz, un crash o un cierre de Excel no trunque `direcciones.csv`.

**Por qué:** `matriz_ficha.escribe_ficha` y `recepcion.escribe` escriben en sitio; no hay tmp+replace ni `.bak`.

**Alcance permitido:** `tools/matriz_ficha.py`, `tools/recepcion.py`, `tools/csvio.py` (nuevo), `tests/test_csvio.py` (nuevo).

**Prohibido:** cambiar el contrato de 3 columnas; tocar datos reales sin backup; cambiar el orden de las filas.

**Pasos:**

1. Crear `csvio.write_atomic(path, rows, fieldnames, encoding="utf-8-sig", delimiter=";")`:
   - escribe en `path.with_suffix(".tmp")` en el mismo directorio;
   - `flush` + `os.fsync` + `close`;
   - copia `path` a `path.with_suffix(".bak")` (una generación);
   - `os.replace(tmp, path)`;
   - en excepción, borra el tmp y no toca el original.
2. Reemplazar la escritura directa en `matriz_ficha.escribe_ficha` y `recepcion.escribe`.
3. Unificar encoding y delimiter: `utf-8-sig` + `;` para ambos.
4. Test de fallo inyectado: si `writerow` lanza a la mitad, el hash del original no cambia y no queda `.tmp`.
5. Test de round-trip: 2168 filas, 206 fichas, acentos, `;` y ficha multilínea.

**Aceptación:**

```powershell
python -m pytest tests/test_csvio.py -q
# Esperado: 0 failed.

# Round-trip sobre una copia, no sobre el original:
python -c "from tools import csvio; ..."
# Esperado: 2168 filas, 206 fichas, BOM, separador ';'.
```

- `Select-String -Path tools\matriz_ficha.py,tools\recepcion.py -Pattern "write_bytes|open\(.*[\"']w[\"']"`
  solo debe mostrar el helper, no escrituras directas.

**Evidencia:** `evidencia/WP-03/pytest.txt`, `roundtrip.txt`, hashes antes/después.

**Rollback:** restaurar los dos módulos; el `.bak` queda como red de seguridad.

**Estimación:** 6 h.

---

### WP-04 — Identidad de la hoja: fail-closed

**Objetivo:** que el agente no pegue si no puede confirmar que la pestaña y la cabecera son las correctas.

**Por qué:** `hoja.py:49` deja pasar cuando no hay captura o texto. Es el riesgo más caro: datos en la hoja equivocada.

**Alcance permitido:** `tools/hoja.py`, `tools/cp.py`, tests.

**Prohibido:** pegar a ciegas; cambiar el flujo de pegado; tocar la hoja real durante las pruebas.

**Pasos:**

1. Agregar `hoja.identidad()` que lea la zona de pestaña/título y exija:
   - título o URL de Google Sheets;
   - nombre de hoja configurado (`HOJA_TITULO`, por defecto el que ya usa el proyecto);
   - cabeceras esperadas en la misma banda.
2. Si no hay captura o el OCR vuelve vacío: reintentar 2 veces y devolver `False`.
3. `cp` llama a `identidad()` antes de pegar; si `False`, `Halt` con `requiere_revision` y no pega.
4. `HOJA_FAIL_OPEN=1` solo como escape heredado, default `0`; si se usa, registrar en el ledger y avisar.
5. Tests con imágenes/texto simulados: `None` → `False`; título incorrecto → `False`; correcto → `True`.

**Aceptación:**

```powershell
python -m pytest tests/test_hoja.py tests/test_cp.py -q
# Esperado: 0 failed.

# Dry-run con la hoja equivocada al frente:
python tools/loop.py --dry --solo D01
# Esperado: no pega; estado requiere_revision; mensaje "hoja no verificada".
```

- `Select-String -Path tools\hoja.py -Pattern "fallo abierto"` ya no aparece como default.

**Evidencia:** `evidencia/WP-04/pytest.txt`, `dry-wrong-tab.txt`, captura de la pestaña correcta.

**Rollback:** restaurar `hoja.py` y `cp.py`; el comportamiento fail-open vuelve solo si se restaura el archivo.

**Estimación:** 8 h. Riesgo: el OCR de la pestaña puede ser frágil; probar en la pantalla real y con la hoja abierta.

---

### WP-05 — Endurecer el panel

**Objetivo:** que el panel no sea una puerta abierta en la red local.

**Por qué:** token de 32 bits, bind `0.0.0.0`, HTTP, token en URL y endpoint que mata procesos.

**Alcance permitido:** `tools/ui.py`, `arranca.bat`, tests.

**Prohibido:** exponer el panel a Internet; cambiar el diseño visual; agregar usuarios.

**Pasos:**

1. Token `secrets.token_urlsafe(16)` (>= 22 caracteres). Si `ui_token.txt` tiene menos, rotarlo.
2. Bind default `127.0.0.1`; `MATRIZ_UI_BIND=0.0.0.0` solo opt-in explícito.
3. Autenticación solo por header `X-Token`; eliminar `?k=` (o aceptarlo deprecado por una corrida, con log).
4. Rate limit simple: 20 requests/min por IP; responder 429.
5. `/api/matar`: solo POST + `confirm=1`; si falta, 400.
6. ACL de `datos\ui_token.txt`: solo el usuario actual (`icacls`), o mover el token a variable de entorno.
7. `arranca.bat` no imprime el token en pantalla; lo guarda en el archivo con ACL.

**Aceptación:**

```powershell
# Sin token:
Invoke-WebRequest http://127.0.0.1:8765/api/estado -UseBasicParsing
# Esperado: 401.

# Con token:
Invoke-WebRequest http://127.0.0.1:8765/api/estado -Headers @{ "X-Token" = $tok } -UseBasicParsing
# Esperado: 200.

Get-NetTCPConnection -LocalPort 8765 | Select-Object LocalAddress
# Esperado: 127.0.0.1 (no 0.0.0.0).
```

- `python -c "import secrets; print(len(secrets.token_urlsafe(16)))"` >= 22.
- 21 requests en un minuto → 429.

**Evidencia:** `evidencia/WP-05/auth.txt`, `bind.txt`, `rate-limit.txt`.

**Rollback:** restaurar `ui.py` y `arranca.bat`; rotar el token.

**Estimación:** 6 h.

---

### WP-06 — Higiene de secretos y PII

**Objetivo:** que ninguna clave, token o dirección quede en el árbol que se comparte.

**Por qué:** `.gitignore` no cubre `config/jev.json` ni `datos/ui_token.txt`; hay archivos con direcciones fuera de `datos/`.

**Alcance permitido:** `.gitignore`, `scripts/check_secrets.ps1` (nuevo), `docs/PRIVACY.md`, `README.md`, ACLs.

**Prohibido:** borrar datos sin backup; publicar el repo; cambiar la visibilidad sin aprobación.

**Pasos:**

1. Agregar a `.gitignore`:
   ```
   config/*.json
   !config/*.example.json
   datos/ui_token.txt
   datos/direcciones_problema.txt
   datos/direcciones_orden.csv
   evidencia/
   datos/traza.jsonl
   datos/control.json
   datos/supervisor.lock
   datos/fichas_pendientes.csv
   ```
2. `scripts/check_secrets.ps1`: buscar `oc_sk_`, `api_key`, `password`, `Bearer`, `token=` en archivos de texto; excluir `config/*.example.json` y `docs/`.
3. Rotar cualquier clave que haya estado en el árbol o en un ZIP compartido.
4. `docs/PRIVACY.md`: inventario de datos, retención, acceso, terceros, cómo borrar.
5. Decidir con el operador si `direcciones.csv` y `ledger.csv` se versionan. Recomendación: no; si se versionan, repo privado y acceso mínimo.

**Aceptación:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_secrets.ps1
# Esperado: exit 0, "sin secretos".

# Prueba negativa:
"oc_sk_test_fake" | Out-File "$env:TEMP\fake-secret.txt"
powershell -ExecutionPolicy Bypass -File scripts\check_secrets.ps1 -Path $env:TEMP
# Esperado: exit 1 y el archivo detectado.
```

- `.gitignore` contiene las rutas.
- `icacls datos\ui_token.txt` muestra solo al usuario actual.

**Evidencia:** `evidencia/WP-06/secret-scan.txt`, `.gitignore`, `icacls.txt`.

**Rollback:** restaurar `.gitignore`; las claves rotadas no se pueden "des-rotar" (por eso se rota al final).

**Estimación:** 3 h.

**Gate 1 — salida:** S1 = 0; los 6 WP con evidencia; operador aprueba PII y panel. Si falta una aprobación, no se pasa a G2.

---

## 6. Gate 2 — Integridad y operación

### WP-07 — Un solo contrato de entrada

**Objetivo:** eliminar el camino muerto `datos/datos.csv` y dejar `direcciones.csv` como única fuente.

**Por qué:** `loop.py` conserva `DATOS`/`lee_datos`, los tests los usan y tres docs hablan de `datos.csv`; el archivo real solo tiene cabecera.

**Alcance permitido:** `tools/loop.py`, `tests/test_loop.py`, `RONDA_PRUEBAS.md`, `PROMPT_OBRERO_T-IBM-01.md`, `TRACE_FUNCIONES.md`, `docs/PLAN_0.2.md`.

**Pasos:**

1. Eliminar `DATOS`, `lee_datos` y sus usos; si se quiere conservar compatibilidad, dejar un wrapper que delegue en `lee_direcciones` y marcar deprecado.
2. Actualizar docs: `datos.csv` → `direcciones.csv`; 6 columnas → 3 columnas.
3. Test de contrato: `lee_direcciones()` lee 3 columnas, asigna `D01`, conserva acentos y `;`.
4. `datos/datos.csv` se elimina o se mueve a `datos/legacy/` como fixture, nunca como entrada.

**Aceptación:**

```powershell
Select-String -Path tools\*.py,tests\*.py -Pattern "datos\.csv|lee_datos|DATOS\s*="
# Esperado: 0 matches (salvo legacy documentado).

python -m pytest tests/test_loop.py -q
# Esperado: 0 failed.
```

**Evidencia:** `evidencia/WP-07/grep.txt`, `pytest.txt`.

**Estimación:** 4 h.

---

### WP-08 — Id estable o bloqueo de edición

**Objetivo:** que fichas y ledger no se desalineen si el operador ordena o filtra el CSV.

**Por qué:** el id `D01` es posicional; `escribe_ficha` usa `int(id)-1`.

**Alcance permitido:** `tools/matriz_ficha.py`, `tools/loop.py`, `datos/ids.csv` (nuevo sidecar), tests.

**Pasos (opción recomendada: sidecar):**

1. Crear `datos/ids.csv` con `id,parte1,parte2,hash`.
2. Si no existe, generarlo desde `direcciones.csv` en la primera corrida.
3. `hash = sha256(parte1 + "|" + parte2)[:12]`.
4. `escribe_ficha` busca el id por hash, no por posición.
5. Si el hash no existe (dirección editada), crear un id nuevo y registrar `requiere_revision`.
6. Opción mínima si no se quiere sidecar: bloquear la edición del CSV durante la corrida (lock de WP-10) y documentarlo.

**Aceptación:**

```powershell
python -m pytest tests/test_ids.py -q
# Esperado: reordenar el CSV no cambia el id de la misma dirección.
```

- Dry-run con el CSV reordenado: la ficha se escribe en la fila correcta.

**Evidencia:** `evidencia/WP-08/reorder-test.txt`.

**Estimación:** 8 h.

---

### WP-09 — Reconciliación pre-corrida

**Objetivo:** detectar que la hoja cambió por fuera antes de reanudar.

**Por qué:** `reanuda_desde` confía en `paginas_vistas`; una edición externa puede duplicar o saltar páginas.

**Alcance permitido:** `tools/loop.py`, `datos/run.json` (nuevo), `tools/supervisor.py`, tests.

**Pasos:**

1. Al iniciar una corrida, escribir `datos/run.json` con `run_id`, `inicio`, `sheet`, `ultima_fila_ledger`.
2. Antes de reanudar, pedir/leer la última fila de la hoja; si no coincide con la esperada, abortar con `requiere_revision`.
3. Si no se puede leer la hoja, exigir confirmación manual del operador y registrarla en `run.json`.
4. No pegar nada si la reconciliación falla.

**Aceptación:**

```powershell
python tools/loop.py --dry --solo D02
# Con una fila extra simulada en la hoja: aborta, no pega, estado requiere_revision.
```

**Evidencia:** `evidencia/WP-09/reconciliacion.txt`.

**Estimación:** 6 h.

---

### WP-10 — Lock de aplicación y heartbeat

**Objetivo:** que dos procesos no hagan read-modify-write del ledger ni peguen a la vez.

**Por qué:** `supervisor.lock` solo protege al supervisor; `loop.py` y `autonomo.py` pueden correr en paralelo.

**Alcance permitido:** `tools/lock.py` (nuevo), `tools/loop.py`, `tools/autonomo.py`, `tools/supervisor.py`, tests.

**Pasos:**

1. `lock.acquire(path)` con `os.open(O_CREAT|O_EXCL)`; escribir PID + timestamp.
2. Si existe, leer PID y comprobar si vive (`tasklist /FI "PID eq <pid>"`); si no vive, borrar y reintentar.
3. Heartbeat cada 60 s; si el proceso muere, el lock queda stale y se limpia.
4. Liberar en `finally`.
5. Usar el mismo lock en `loop.main`, `autonomo.main` y `supervisor.main`.

**Aceptación:**

```powershell
# Dos procesos a la vez:
python tools/loop.py --dry --solo D01
python tools/loop.py --dry --solo D02
# Esperado: el segundo exit 2, "lock held by PID ...".
```

**Evidencia:** `evidencia/WP-10/lock.txt`.

**Estimación:** 4 h.

---

### WP-11 — Runner único y conteo real de tests

**Objetivo:** una sola cifra de tests, generada por una corrida, no por copiar y pegar.

**Por qué:** hay 11 cifras distintas y 391 `def test_` estáticos; nadie sabe cuál es la verdad.

**Alcance permitido:** `scripts/verify.ps1` (nuevo), `tools/verifications/` (nuevo), `README.md`, docs de estado.

**Pasos:**

1. `scripts/verify.ps1`:
   - `python -m compileall -q tools`;
   - detectar runner (`pytest` si está; si no, `unittest discover`);
   - correr la suite completa;
   - guardar salida en `tools/verifications/verify-<timestamp>.txt` y JSON con `total`, `passed`, `failed`, `skipped`;
   - escribir `tools/verifications/test_count.txt`.
2. README y docs toman el número del artefacto. No se escribe a mano.
3. Si hay tests que requieren GUI/Excel, marcarlos `skip` con motivo y contarlos aparte.

**Aceptación:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
# Esperado: exit 0, artefacto JSON, test_count.txt con un número.
```

**Evidencia:** `tools/verifications/verify-*.json`.

**Estimación:** 3 h.

---

### WP-12 — Matar solo los procesos del proyecto

**Objetivo:** que `/api/matar` no mate un `supervisor.py` ajeno.

**Por qué:** `ui.matar` filtra por nombre de comando y puede matar procesos de otro proyecto.

**Alcance permitido:** `tools/ui.py`, `tools/supervisor.py`, `datos/workers.json` (nuevo), tests.

**Pasos:**

1. El supervisor registra los PID que lanza en `datos/workers.json`.
2. `/api/matar` mata solo esos PID (y sus hijos).
3. Fallback: filtrar por `CommandLine` que contenga la ruta del proyecto, no solo el nombre.
4. Limpiar PID muertos del registro.

**Aceptación:**

```powershell
# Crear un supervisor.py decoy en otra carpeta; ejecutar /api/matar.
# Esperado: el decoy sigue vivo; el worker del proyecto muere.
```

**Evidencia:** `evidencia/WP-12/kill.txt`.

**Estimación:** 3 h.

---

### WP-13 — Reconciliación documental y ADRs

**Objetivo:** una sola verdad documental; nada de claims falsos.

**Por qué:** ADR-0004 append-only vs upsert; Alt+Tab vs taskbar; `tools/flow.py` inexistente; README dice que `config/jev.json` existe; T2 “HECHO” sin modularización.

**Alcance permitido:** `README.md`, `docs/`, `tools/README.md`, `ESTADO_ORQUESTACION.md`, `docs/adr/`.

**Pasos:**

1. Crear `docs/adr/ADR-0007-ledger-upsert.md` (supersede ADR-0004): el ledger hace upsert por id, no append-only.
2. Crear `docs/adr/ADR-0008-jev-pii.md` como **Propuesto** (supersede ADR-0006): clave dedicada, sin credencial personal, opt-in. Requiere aprobación del operador (D-01) antes de marcarlo como Aceptado.
3. Banner “Superado por ADR-0007” en ADR-0004. En ADR-0006: “Ver ADR-0008 (Propuesto); se marca superado solo si D-01 se aprueba”. No borrar los originales.
4. Corregir `DISENO_FLUJO_DEFINITIVO.md`: Alt+Tab → clic en taskbar.
5. Corregir `tools/README.md`: append-only → upsert; Alt+Tab → taskbar; `_experimentos` no existe.
6. Corregir `TRACE_FUNCIONES.md`: `tools/flow.py` → `matriz_buscar.py`/`ciclo.py`.
7. Corregir `README.md`: conteo de tests desde artefacto; `config/jev.json` no viene; 128 archivos; perfil default `rapido`.
8. Corregir `PLAN_VERSION_FINAL.md`: T2 “PARCIAL (fachadas; loop.py 1036 líneas)”; T5 “HECHO con medición pendiente”; corrida 121/1710 “sin evidencia en el ledger entregado”.
9. Corregir `GUIA_DE_USO.md`: 345 tests → número del artefacto; 20,4 s/dir → medición con fecha; nota de fail-open.
10. Corregir `RONDA_PRUEBAS.md` y `PROMPT_OBRERO_T-IBM-01.md`: `datos.csv` → `direcciones.csv`; Ctrl+C/celda por celda → supersedido por portapapeles.
11. Corregir `ESCALAMIENTO.md`: append-only → upsert; 105 tests → número real.
12. Elegir un nombre canónico: `IBM AnyControl` (producto) / `ibm-anycontrol` (repo). Reemplazar `matriz-ibm-agent` e `IBM AGENT` donde sea nombre de producto.
13. Agregar entrada 2026-11-18 a `ESTADO_ORQUESTACION.md` con: crítica, plan, WPs, responsable y estado.
14. Mover planes viejos a `docs/archive/` y dejar un índice.

**Aceptación:**

```powershell
Select-String -Path README.md,docs\*.md,tools\README.md -Pattern "394 tests|345 tests|append-only|Alt\+Tab|flow\.py|config/jev\.json ya"
# Esperado: 0 matches (o solo en docs/archive).
```

- ADR-0007 existe; ADR-0008 existe como **Propuesto** y la decisión D-01 está registrada.
- `ESTADO_ORQUESTACION.md` tiene la entrada nueva.
- El README toma el conteo de `tools/verifications/test_count.txt`.

**Evidencia:** `evidencia/WP-13/grep.txt`, ADRs, diff.

**Estimación:** 6 h.

**Gate 2 — salida:** P1 cerrado o waiver; suite verde; docs sin claims falsos.

---

## 7. Gate 3 — Auditoría y release

1. Ejecutar `scripts/verify.ps1` completa; guardar artefacto.
2. Ejecutar un dry-run autorizado (`python tools/loop.py --dry --solo D01`) y guardar log.
3. Restaurar el backup de WP-00 en una carpeta temporal y comparar hashes de los archivos críticos.
4. Completar `DOSSIER_CIERRE_TEMPLATE.md` con evidencia real.
5. Revisor ciego re-ejecuta 3 acceptance al azar (mínimo: WP-03, WP-04, WP-05).
6. Firmar veredicto: CERRADO / CERRADO CON RESERVAS / RECHAZADO.
7. Crear release candidate:
   - si hay git local: tag `v1.0.0-finiquito`;
   - si no: ZIP `IBM-AnyControl-v1.0.0-finiquito.zip` + SHA256.
8. Entregar `README_OPERACION.md` (nuevo): arranque, parada, panel, recuperación, límites conocidos, contactos.
9. Archivar el dossier y los artefactos en `FINIQUITO/evidencia/`.

**Criterio de release:** DoD completo; revisor ciego firma; operador acepta.

---

## 8. Orden, dependencias y estimación

| Orden | WP | Depende de | Estimación |
|---|---|---|---|
| 1 | WP-00 | — | 0,5 d |
| 2 | WP-01 | WP-00 | 0,5 d |
| 3 | WP-02 | WP-00 | 0,5 d |
| 4 | WP-03 | WP-00 | 0,75 d |
| 5 | WP-04 | WP-00, WP-03 | 1 d |
| 6 | WP-05 | WP-00 | 0,75 d |
| 7 | WP-06 | WP-02, WP-05 | 0,5 d |
| 8 | WP-07 | WP-03 | 0,5 d |
| 9 | WP-08 | WP-07 | 1 d |
| 10 | WP-09 | WP-08, WP-10 | 0,75 d |
| 11 | WP-10 | WP-00 | 0,5 d |
| 12 | WP-11 | WP-00 | 0,5 d |
| 13 | WP-12 | WP-10 | 0,5 d |
| 14 | WP-13 | todos | 0,75 d |
| 15 | Gate 3 | todos | 1–2 d |

No paralelizar WP-03/04/07/08/09: tocan el mismo flujo de datos. WP-05/06/11/12 pueden ir en paralelo si hay dos personas.

---

## 9. Matriz de riesgos

| ID | Riesgo | Prob. | Impacto | Severidad | Mitigación | Disparador |
|---|---|---|---|---|---|---|
| R-01 | Corrupción de `direcciones.csv` | Media | Alto | S1 | WP-03 atómico + `.bak` + restore | Hash distinto o filas < 2168 |
| R-02 | PII a tercero (Jev) | Alta | Alto | S1 | WP-02 opt-in + clave dedicada | Log de request a opencode.ai |
| R-03 | Pegado en hoja equivocada | Media | Alto | S1 | WP-04 fail-closed + identidad | `hoja no verificada` |
| R-04 | Intrusión al panel | Media | Alto | S1 | WP-05 localhost + token fuerte | 401/429 anómalos |
| R-05 | Doble pegado tras crash | Media | Alto | S1 | WP-09 reconciliación + WP-10 lock | `pegando` sin cierre |
| R-06 | Entrega no arranca | Alta | Medio | S1 | WP-01 preflight | `setup.ps1 -Check` falla |
| R-07 | Regresión no detectada | Media | Medio | S2 | WP-11 runner + artefacto | Suite roja o conteo cambia |
| R-08 | Desalineación de id | Media | Medio | S2 | WP-08 sidecar o lock | CSV reordenado |
| R-09 | Matar proceso ajeno | Baja | Medio | S2 | WP-12 PID registry | Proceso ajeno muere |
| R-10 | Deriva documental | Alta | Bajo | S2 | WP-13 + grep de cierre | Claim viejo en README |
| R-11 | OCR de pestaña frágil | Media | Medio | S2 | WP-04 fallback + prueba real | Falso negativo repetido |
| R-12 | Edición del CSV en corrida | Media | Alto | S1 | WP-08/10 lock + aviso | Filas cambian durante run |

**Regla:** un riesgo S1 no se acepta con waiver. Se cierra o se cancela el release.

---

## 10. Correcciones documentales exactas

| # | Archivo | Claim actual | Corrección | WP |
|---|---|---|---|---|
| 1 | `README.md` | “394 tests” | Número desde `tools/verifications/test_count.txt` | WP-11/13 |
| 2 | `README.md` | `config/jev.json` “ya contiene endpoint, modelo y clave” | “No viene; crear desde `config/jev.example.json` o definir `MATRIZ_JEV_KEY`” | WP-01/02 |
| 3 | `README.md` | 126 archivos | 128 archivos (o quitar el conteo) | WP-13 |
| 4 | `README.md` | perfil default `psicopata` | default `rapido`; `psicopata` explícito | WP-01 |
| 5 | `docs/adr/ADR-0004-ledger-append-only.md` | ledger append-only | Banner: “Superado por ADR-0007; el ledger hace upsert por id” | WP-13 |
| 6 | `docs/adr/ADR-0006-jev-como-segunda-opinion.md` | auth en `%LOCALAPPDATA%` / segunda opinión | Aviso: “Ver ADR-0008 (Propuesto); se marca superado solo si D-01 se aprueba” | WP-02/13 |
| 7 | `docs/DISENO_FLUJO_DEFINITIVO.md` | Alt+Tab para volver a la hoja | Clic en el icono de la taskbar (o el método que use `cp.py`) | WP-13 |
| 8 | `tools/README.md` | ledger append-only; Alt+Tab | Upsert; clic en taskbar | WP-13 |
| 9 | `docs/engineering/TRACE_FUNCIONES.md` | cita `tools/flow.py` | `matriz_buscar.py` / `ciclo.py` | WP-13 |
| 10 | `docs/PLAN_VERSION_FINAL.md` | T2 “HECHO (módulos temáticos)” | “PARCIAL: fachadas de 14/32 líneas; `loop.py` sigue en 1036 líneas” | WP-13 |
| 11 | `docs/PLAN_VERSION_FINAL.md` | T5 “HECHO” y “pendiente de medir en vivo” | “HECHO con medición pendiente; adjuntar artefacto” | WP-13 |
| 12 | `docs/PLAN_VERSION_FINAL.md` | corrida 121 dir / 111 ok / 1710 filas | “Sin evidencia en el ledger entregado (52 filas / 44 ok)” | WP-13 |
| 13 | `docs/GUIA_DE_USO.md` | 345 tests; 20,4 s/dir | Número real; medición con fecha y equipo; nota de fail-open | WP-11/13 |
| 14 | `RONDA_PRUEBAS.md`, `PROMPT_OBRERO_T-IBM-01.md` | `datos.csv` 6 columnas; Ctrl+C/celda por celda | `direcciones.csv` 3 columnas; portapapeles (Shift+clic) | WP-07/13 |
| 15 | `docs/engineering/ESTADO_ORQUESTACION.md` | sin entrada 2026-11-03 | Agregar entrada 2026-11-18 con crítica, plan y WPs | WP-13 |
| 16 | `ESCALAMIENTO.md` | append-only; 105 tests | Upsert; número real de tests | WP-13 |
| 17 | varios | `IBM AGENT`, `matriz-ibm-agent`, `ibm-anycontrol` | Nombre canónico: `IBM AnyControl` / repo `ibm-anycontrol` | WP-13 |

---

## 11. Formato REPORTA y dossier

Cada WP termina con:

```text
REPORTA
- WP: <id>
- Snapshot/commit: <hash o ruta del ZIP>
- Aceptación: <comando + output pegado, por cada criterio>
- Archivos tocados: <lista>
- Fuera de alcance: NINGUNO | <lista + justificación>
- Evidencia: FINIQUITO/evidencia/<WP>/
- Tests: <antes/después>
- Riesgos/deuda: <lista | NINGUNO>
```

El dossier final se completa en `DOSSIER_CIERRE_TEMPLATE.md`.

---

## 12. Criterios de STOP

Detener y escalar si:

1. Una aceptación falla dos veces en el mismo WP.
2. Un test cambia después de un refactor (revertir, no "arreglar" el test).
3. Aparece un archivo modificado fuera de alcance sin declarar.
4. La suite queda roja después de un cambio.
5. No hay backup verificado antes de tocar datos.
6. Se detecta una clave o PII en un lugar no previsto.
7. El operador no aprueba PII, panel o ventana de corrida.
8. El proveedor de modelo/Jev no está disponible y no hay vía alternativa sana.

---

## 13. Waivers

Solo para P1/P2. Formato:

```text
WAIVER
- Riesgo:
- Motivo:
- Alcance:
- Vigencia:
- Mitigación compensatoria:
- Aprobado por:
- Fecha:
```

Nunca para S1. Nunca para "no hice el backup".

---

## 14. Anexo A — Prompts congelados (P0)

### T-FIN-00 — Baseline

```text
Objetivo: congelar el estado del proyecto IBM AGENT antes de cualquier cambio.
Alcance: crear ZIP, manifiesto SHA256 y prueba de restore; no editar código ni datos.
Prohibido: ejecutar loop/supervisor/autonomo; tocar direcciones.csv o ledger.csv.
Aceptación:
1. ZIP existe y contiene >=128 archivos.
2. Manifiesto >=128 filas.
3. Restore: hashes coinciden; conteos 2168/52/2167.
4. Operador confirma por escrito.
REPORTA con rutas, hashes y output.
```

### T-FIN-01 — Preflight

```text
Objetivo: que arranca.bat falle claro o arranque; default rapido; config example.
Alcance: arranca.bat, setup.ps1, config/jev.example.json, README.
Prohibido: descargar dependencias sin aprobación; crear credenciales.
Aceptación: setup.ps1 -Check exit 2 sin venv y exit 0 con venv; arranca.bat no arranca si falla; psicopata no es default.
REPORTA con outputs.
```

### T-FIN-02 — PII/Jev

```text
Objetivo: Jev off por defecto; sin credencial personal; PRIVACY.md.
Alcance: _jev.py, estado.py, loop.py, config/jev.example.json, docs/PRIVACY.md.
Prohibido: usar %USERPROFILE% auth.json; enviar PII sin opt-in.
Aceptación: disponible() False sin clave; test que ask no se llama con MATRIZ_JEV=0; grep USERPROFILE=0; PRIVACY.md existe.
REPORTA con outputs.
```

### T-FIN-03 — CSV atómico

```text
Objetivo: escritura atómica de direcciones.csv con .bak y tmp+replace.
Alcance: matriz_ficha.py, recepcion.py, csvio.py, tests.
Prohibido: cambiar contrato de 3 columnas; tocar el CSV real sin backup.
Aceptación: test de fallo inyectado deja hash intacto; round-trip 2168/206/BOM/;; grep de escrituras directas=0.
REPORTA con pytest y hashes.
```

### T-FIN-04 — Hoja fail-closed

```text
Objetivo: no pegar si no se confirma pestaña/cabecera.
Alcance: hoja.py, cp.py, tests.
Prohibido: pegar a ciegas; tocar la hoja real en pruebas.
Aceptación: None→False; título incorrecto→False; correcto→True; dry-run con hoja equivocada no pega y marca requiere_revision.
REPORTA con pytest y log.
```

### T-FIN-05 — Panel

```text
Objetivo: panel localhost, token >=22, header, rate limit, matar con confirmación.
Alcance: ui.py, arranca.bat, tests.
Prohibido: exponer a Internet; agregar usuarios.
Aceptación: sin token 401; con token 200; bind 127.0.0.1; 21 req→429; token >=22.
REPORTA con outputs.
```

### T-FIN-06 — Higiene

```text
Objetivo: .gitignore, check_secrets.ps1, ACL de ui_token, PRIVACY.md.
Alcance: .gitignore, scripts/check_secrets.ps1, docs/PRIVACY.md, README, ACLs.
Prohibido: borrar datos; publicar repo.
Aceptación: scan exit 0; fake secret exit 1; .gitignore contiene rutas; icacls solo usuario actual.
REPORTA con outputs.
```

---

## 15. Anexo B — Decisiones que debe tomar el operador

| ID | Decisión | Opciones | Efecto |
|---|---|---|---|
| D-01 | Jev on/off | A) off por defecto (recomendado); B) on con clave dedicada y DPA | PII vs velocidad de clasificación |
| D-02 | ¿Versionar datos? | A) no (recomendado); B) sí, repo privado | PII en historial |
| D-03 | Panel en LAN | A) localhost (recomendado); B) LAN con token y firewall | Comodidad vs exposición |
| D-04 | Git local | A) sí, sin remoto; B) snapshots ZIP | Rollback y auditoría |
| D-05 | Ventana de corrida real | Fecha/hora y responsable | Evita solapamientos |
| D-06 | Revisor ciego | Nombre | Firma del cierre |
| D-07 | Waivers P1 | Aceptar/rechazar | Alcance del release |

---

## 16. Anexo C — Glosario

- **EF:** Encargado de Finiquito.
- **P0/S1:** riesgo crítico que bloquea producción.
- **Gate:** punto de control con criterio de salida.
- **WP:** work package, unidad de trabajo con aceptación.
- **Fail-closed:** ante duda, no pega.
- **Fail-open:** ante duda, deja pasar (lo que hay que eliminar).
- **Upsert:** insertar o actualizar por id, sin duplicar.
- **Snapshot:** copia ZIP + hash del estado.
- **Waiver:** excepción firmada para un riesgo P1/P2.
- **Revisor ciego:** quien no implementó y firma el cierre.
