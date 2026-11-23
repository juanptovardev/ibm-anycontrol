# Retoma de sesion

Fecha: 2026-11-19. Documento de continuidad. No reemplaza a `FINIQUITO/` ni a `docs/engineering/ESTADO_ORQUESTACION.md`.

## 1. Estado del proyecto

Repositorio remoto
- `https://github.com/juanptovardev/ibm-anycontrol`, privado, rama por defecto `main`.
- `main` y `release/1.1-oficial-funcional` apuntan a `547a5c0`.
- Tags publicados: `v1.0` (`bf57994`) y `v1.0.1` (`0104a38`). No existe tag `v1.1`.
- La rama v1.1 preserva los datos operativos de GitHub (`git diff 48c6a8c origin/main -- datos/ config/` vacio).

Carpeta local definitiva
- `C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT` (sin `.git`).
- Contiene el FINIQUITO ejecutado hasta WP-08, con evidencia en `FINIQUITO/evidencia/WP-00..WP-08`.
- Cambios locales sin commitear ni subir: `FINIQUITO/`, `docs/PRIVACY.md`, `setup.ps1`, `scripts/check_secrets.ps1`, `tools/csvio.py`, `tests/test_csvio.py`, `tests/test_ids.py`, `.gitignore` nuevo, y ajustes de WP-01 a WP-08.
- Residuo a limpiar antes de publicar: `tools/__pycache__/` y `tests/__pycache__/`.

Copia secundaria
- `C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT - copia` (datos sincronizados desde el remoto el 2026-11-18).

Base operativa original
- `C:\Users\juanp_8h8f07l\dev\matriz-ibm-agent-piloto100` (rama `piloto100`, HEAD `48c6a8c`). Es la fuente de fichas usada en el analisis de hoy.

## 2. Trabajo interrumpido antes de esta pausa

Tarea: unificar la version visible a 1.1 y corregir afirmaciones falsas en la documentacion, con criterio anti-slop, y publicar en `main`.

Pendiente, sin ejecutar:
- README: `# IBM AnyControl v1` (linea 1), `(tag v1.0)` (linea 9), `Configura IBM AnyControl v1` (linea 51), `394 tests` (lineas 13 y 205 -> 450 medidos o "conteo desde artefacto").
- `append-only` -> upsert por id en: `ESCALAMIENTO.md`, `docs/DISENO_FLUJO_DEFINITIVO.md`, `docs/MODULARIZACION.md`, `docs/engineering/ESTADO_ORQUESTACION.md`, `docs/engineering/FLUJO_PEGADO.md`, `docs/engineering/TRACE_FUNCIONES.md`, `tools/README.md`.
- `Alt+Tab` -> cambio por iconos de taskbar (hecho en T5) donde se describe el presente, no en el registro historico.
- `datos/datos.csv` de 6 columnas -> `datos/direcciones.csv` (`parte1;parte2;ficha`) en `docs/engineering/GUIA_ORQUESTACION_IA.md`, `docs/engineering/TRACE_FUNCIONES.md`, `docs/PROMPT_ARRANQUE.md`.
- `tools/flow.py` inexistente -> `tools/matriz_buscar.py`, `tools/ciclo.py`, `tools/paso1.py`, `tools/paso2.py`.
- `config/jev.json` real -> solo `config/jev.example.json` (Jev apagado por defecto, D-01).
- Crear `docs/adr/ADR-0007-ledger-upsert.md` y `docs/adr/ADR-0008-jev-y-pii.md` (Propuesto), con aviso de supersesion en ADR-0004 y ADR-0006.
- Anadir entrada fechada en `docs/engineering/ESTADO_ORQUESTACION.md`.
- Mover planes obsoletos a `docs/archive/` con indice: `PLAN_0.2`, `PLAN_PRUEBA_COMPLETA`, `RONDA_PRUEBAS`, `TABLA_RANGOS`, `PLAN_VERSION_FINAL`, `INFORME_CRITICA_ESTATICA_2026-11-18`, `HANDOFF_CRITICA_SESION_NUEVA`, `PLAN_DEFINITIVO_MEJORAS`.
- No editar `PROMPT_OBRERO_T-IBM-01.md`: es prompt congelado, las erratas van en launcher o en RONDA.
- Commit y push a `main`. Procedimiento probado: clonar a `%TEMP%`, copiar el arbol sin `.git`, commit con autor `juanptovardev <juanptovardev@users.noreply.github.com>`, push.

Trabajo de finiquito sin evidencia: WP-09 (reconciliacion pre-corrida), WP-10 (lock de aplicacion), WP-11 (runner unico de verificacion), WP-12 (kill acotado por PIDs del proyecto), WP-13 (documentacion y ADRs). Ver `FINIQUITO/CHECKLIST_FINIQUITO.md`.

## 3. Trabajo de esta pausa

Pedido: para cada linea de `Downloads\resultadopruebasagentibm.csv`, dejar columna A intacta, B numero de cuenta matriz de la ficha, C nombre del edificio, D parte1 y parte2 unidas como direccion de referencia inicial.

Hecho: analisis de viabilidad y cobertura. Sin ejecucion, sin escribir la salida.
Resultado: `docs/AUDITORIA_CRUCE_FICHAS_2026-11-19.md`.

Resumen: 3.989 lineas, 319 direcciones distintas, cobertura 69,9% exacta y 92,0% si se admite el alias por direccion interna de la ficha; 5 direcciones sin ficha.

## 4. Orden de retoma recomendado

1. Cerrar el cruce de fichas si el operador da luz verde (genera un archivo nuevo en `Downloads`, no toca el original).
2. Cerrar las correcciones documentales de la seccion 2 y crear ADR-0007 y ADR-0008.
3. Limpiar `__pycache__` y publicar el estado FINIQUITO en `main` (commit unico, mensaje en espanol, sin tag nuevo).
4. Continuar WP-09 a WP-13 del finiquito.

## 5. Reglas vigentes

- No ejecutar tests sin autorizacion expresa.
- No tocar secretos ni datos operativos: uso interno de la empresa, se conservan.
- No asumir acceso a `dev\*` desde la carpeta publicada.
- PowerShell 5.1: no existen `head`, `wc` ni heredoc; usar `Select-Object` y scripts Python en `%TEMP%`.
- Todo comando de shell con timeout explicito.
- Python: `C:\Python314\python.exe` (3.14.3). Git 2.51.2. `gh` autenticado como `juanptovardev`.

## 6. Verificacion rapida del estado

```powershell
git ls-remote https://github.com/juanptovardev/ibm-anycontrol.git refs/heads/main
Test-Path "C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT\FINIQUITO\evidencia\WP-08\full-suite.txt"
Get-ChildItem "C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT\config"
Get-Content "C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT\datos\ledger.csv" -TotalCount 2
```

## 7. Archivos de referencia

- `FINIQUITO/PLAN_DE_FINIQUITO.md`: alcance, gates y work packages.
- `FINIQUITO/DECISIONES_OPERADOR.md`: D-01 a D-07.
- `FINIQUITO/CHECKLIST_FINIQUITO.md`: criterios por WP.
- `docs/AUDITORIA_CRUCE_FICHAS_2026-11-19.md`: analisis del cruce de hoy.
- `docs/engineering/ESTADO_ORQUESTACION.md`: bitacora.
- `datos/ledger.csv`: estado por direccion (13 campos).
- `tools/matriz_ficha.py`: lectura y escritura de la columna `ficha`.