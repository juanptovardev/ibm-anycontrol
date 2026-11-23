# HANDOFF: IBM AGENT - Critica y Analisis (Sesion Nueva, Sin Contexto)

> **Proposito de este documento:** Permitir que una sesion/IA nueva critique y analice el proyecto definitivo sin ningun contexto previo. No ejecutar pruebas; solo revisar, validar coherencia documental, identificar riesgos, deudas tecnicas y proponer mejoras.
> **Fecha de preparacion:** 2026-11-19
> **Ubicacion:** `C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT`
> **Copia de seguridad creada antes de cambios:** `C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT - copia` (126 archivos, intacta)

---

## 1. Que es este proyecto

**IBM AnyControl / matriz-ibm-agent** es un agente autonomo que opera un terminal IBM 5250 remoto (via AnyDesk MCP) para:
1. Leer una lista de direcciones desde `datos/direcciones.csv`.
2. Navegar/buscar cada direccion en el sistema IBM (emulador 5250).
3. Extraer suscriptores/fichas de las cuentas matriz encontradas.
4. Pegar resultados en Google Sheets (hoja "LIMPIEZA RR") y registrar estado en `datos/ledger.csv`.

**Repositorio interno privado.** Contiene contratos y datos operativos reales (direcciones, ledger con evidencias de corridas previas). No es un repositorio git actualmente.

### Estado funcional reportado (de documentacion existente)
- Corrida real de 121 direcciones: 111 ok, 10 no_encontrado, 0 errores, 134 paginas, 1710 filas (~24-25s/direccion).
- Perfiles de velocidad: sigiloso 27.5s, humano 18.3s, rapido 12.2s, psicopata 9.15s (suelo real ~12.6s).
- Suite de tests reportada en versiones previas: ~292-425 tests (segun version/rama); **no se han ejecutado pruebas en esta sesion de consolidacion** por indicacion explicita.

---

## 2. Lo que se hizo en esta consolidacion (sesion orquestadora)

1. **Verificacion de destino:** Se confirmo que `IBM AGENT` existe con 126 archivos y 9 directorios, sin procesos activos relacionados.
2. **Copia de seguridad:** Se creo `IBM AGENT - copia` completa antes de cualquier cambio documental.
3. **Limpieza de basura residual:** Se verifico ausencia de `__pycache__`, `*.pyc`, `*.log`, `*.err`, `*.tmp`, `*.bak`, `prueba_*`, `evidencia/`, `_experimentos/`, `verifications/`. No se detectaron artefactos residuales obvios para eliminar (la copia ya estaba limpia). **No se elimino nada vital**.
4. **Documentacion anadida/actualizada:**
   - `PLAN_DEFINITIVO_MEJORAS.md` (nuevo): plan consolidado de mejoras enterprise.
   - `HANDOFF_CRITICA_SESION_NUEVA.md` (este archivo): contexto completo para critica.
   - `docs/engineering/ESTADO_ORQUESTACION.md` (append-only): entrada de esta sesion.
5. **No se ejecutaron pruebas** (peticion del usuario). No se modifico logica de negocio en `tools/`.

### Decisiones y restricciones respetadas
- No tocar `loop.py` ni puertas de control existentes sin necesidad.
- No mover ni borrar `datos/` operativos (`direcciones.csv`, `ledger.csv`, etc.) ni contratos.
- `config/` permanece vacio (credenciales se resuelven por env vars o `%USERPROFILE%\.matriz\creds.json` segun `tools/credenciales.py`).
- `arranca.bat` depende del venv hermano `..\mcp-anydesk\.venv\Scripts\python.exe`; dependencia externa explicita.

---

## 3. Arbol de archivos (estado actual)

```
IBM AGENT/
  .gitignore  (533 B)
  ESCALAMIENTO.md  (7731 B)
  PLAN_DEFINITIVO_MEJORAS.md  (4126 B)
  PLAN_PRUEBA_COMPLETA.md  (4466 B)
  PROMPT_OBRERO_T-IBM-01.md  (3382 B)
  README.md  (8942 B)
  RONDA_PRUEBAS.md  (9595 B)
  TABLA_RANGOS.md  (1094 B)
  arranca.bat  (842 B)
  config/
  datos/
    datos.csv  (99 B)
    datos_ejemplo.csv  (201 B)
    direcciones.csv  (43055 B)
    direcciones_orden.csv  (9366 B)
    direcciones_problema.txt  (1035 B)
    direcciones_segunda.csv  (36621 B)
    ledger.csv  (10118 B)
  docs/
    DISENO_FLUJO_DEFINITIVO.md  (8435 B)
    GUIA_DE_USO.md  (9623 B)
    MODULARIZACION.md  (4914 B)
    PERFILES_VELOCIDAD.md  (3764 B)
    PLAN_0.2.md  (4076 B)
    PLAN_VERSION_FINAL.md  (16442 B)
    PROMPT_ARRANQUE.md  (5739 B)
    adr/
      ADR-0001-macro-5250-determinista.md  (1563 B)
      ADR-0002-reglas-antes-de-jev.md  (1422 B)
      ADR-0003-clics-viewport-y-foco.md  (1983 B)
      ADR-0004-ledger-append-only.md  (1327 B)
      ADR-0005-limites-emulador-5250.md  (1980 B)
      ADR-0006-jev-como-segunda-opinion.md  (1690 B)
    engineering/
      ESTADO_ORQUESTACION.md  (6923 B)
      EXECUTION_BATCHES.md  (8759 B)
      FLUJO_PEGADO.md  (4565 B)
      GUIA_ORQUESTACION_IA.md  (7453 B)
      TRACE_FUNCIONES.md  (6939 B)
      TRAZA_Y_SEMAFORO.md  (2882 B)
  tests/
    test_anexar_direcciones.py  (2564 B)
    test_anexar_reemplazar.py  (3128 B)
    test_autonomo.py  (5196 B)
    test_autonomo_ledger.py  (4932 B)
    test_bloque_una_fila.py  (6920 B)
    test_buscar_secuencia.py  (3467 B)
    test_clasificador_pixeles.py  (2422 B)
    test_click_sel.py  (3799 B)
    test_contador.py  (5031 B)
    test_cp.py  (2985 B)
    test_dry_merge.py  (4295 B)
    test_enfocar.py  (4791 B)
    test_escribe_ficha_bloqueado.py  (3139 B)
    test_fiabilidad_datos.py  (6440 B)
    test_flujo_definitivo.py  (23454 B)
    test_halt_no_tumba_lote.py  (4016 B)
    test_hoja.py  (2868 B)
    test_integridad_modulos.py  (5326 B)
    test_ir_al_5250.py  (3478 B)
    test_jev.py  (3745 B)
    test_ledger_0_2.py  (4716 B)
    test_loop.py  (2781 B)
    test_mcp_helper.py  (3190 B)
    test_orquesta.py  (2096 B)
    test_pagina.py  (3759 B)
    test_paginar.py  (3964 B)
    test_pausa_recupera.py  (1529 B)
    test_pegado_dudoso.py  (3696 B)
    test_perfil.py  (8266 B)
    test_reanudacion_cli.py  (4685 B)
    test_regenerar_direcciones.py  (4488 B)
    test_reglas.py  (11314 B)
    test_reset_ledger_desde.py  (2857 B)
    test_separar.py  (6590 B)
    test_separar_seguridad.py  (4208 B)
    test_sonda_teclas.py  (839 B)
    test_supervisor.py  (6134 B)
    test_supervisor_ids.py  (3827 B)
    test_t4_ocr_reutilizado.py  (4121 B)
    test_t7_y_e4.py  (2629 B)
    test_tabla.py  (4092 B)
    test_traza.py  (4584 B)
    test_ui_panel.py  (2678 B)
    test_ventana.py  (6014 B)
    test_vigia.py  (1045 B)
    test_vigia_anuncio.py  (4345 B)
    fixtures/
      unidades_ocr.txt  (778 B)
  tools/
    README.md  (5109 B)
    _jev.py  (4722 B)
    _mcp.py  (2284 B)
    anexar_direcciones.py  (5263 B)
    arranque.py  (2955 B)
    autonomo.py  (22557 B)
    bloque.py  (5170 B)
    ciclo.py  (6586 B)
    click_sel.py  (13612 B)
    cp.py  (16201 B)
    credenciales.py  (2148 B)
    enfocar.py  (6103 B)
    estado.py  (19679 B)
    hoja.py  (2789 B)
    login.py  (5110 B)
    loop.py  (51286 B)
    matriz_buscar.py  (4344 B)
    matriz_extraer.py  (568 B)
    matriz_ficha.py  (6365 B)
    native_shot.py  (4629 B)
    nav_prefill.py  (5654 B)
    orquesta.py  (1295 B)
    pagina.py  (12320 B)
    paginar.py  (3564 B)
    paso1.py  (2888 B)
    paso2.py  (2611 B)
    perfil.py  (6265 B)
    preflight_auto.py  (7876 B)
    recepcion.py  (6511 B)
    regenerar_direcciones.py  (5189 B)
    registrar_pegado.py  (1682 B)
    reset_ledger.py  (5783 B)
    rows.py  (4161 B)
    separar.py  (13323 B)
    sonda.py  (1862 B)
    sonda_teclas.py  (2153 B)
    supervisor.py  (17730 B)
    tabla.py  (6094 B)
    tecla.py  (1076 B)
    traza.py  (7456 B)
    ui.py  (13000 B)
    ventana.py  (4370 B)
    vigia.py  (11573 B)
    iconos/
      chrome.png  (991 B)
      emulador5250.png  (770 B)
```

---

## 4. Documentos clave que debes leer (en orden sugerido)

| Prioridad | Documento | Para que |
|---|---|---|
| 1 | `HANDOFF_CRITICA_SESION_NUEVA.md` (este) | Vision global y que criticar |
| 2 | `README.md` | Contratos, modos, operacion, arquitectura general |
| 3 | `PLAN_DEFINITIVO_MEJORAS.md` | Plan de mejoras propuesto (esta sesion) |
| 4 | `docs/PLAN_VERSION_FINAL.md` | Estado medido de version final, T1-T7, pendientes |
| 5 | `docs/GUIA_DE_USO.md` | Operacion, modos, criticas conocidas, riesgos |
| 6 | `docs/DISENO_FLUJO_DEFINITIVO.md` | Flujo B0-B7/P0-P5, estados, reanudacion, guardias |
| 7 | `docs/engineering/ESTADO_ORQUESTACION.md` | Bitacora append-only (historial y ultima entrada) |
| 8 | `docs/engineering/EXECUTION_BATCHES.md` | Batches y prompts congelados, pendientes T-IBM-05/C-01 |
| 9 | `ESCALAMIENTO.md` | Blindaje B1-B8, puertas E0-E3, rendimiento |
| 10 | `docs/PERFILES_VELOCIDAD.md` | Medicion de tiempos y optimizaciones |
| 11 | `docs/MODULARIZACION.md` | Plan de refactor (no ejecutado) |
| 12 | `docs/engineering/TRACE_FUNCIONES.md` | Catalogo de funciones/modulos para evitar duplicacion |
| 13 | `docs/engineering/TRAZA_Y_SEMAFORO.md` | Trazabilidad y semaforo de estado |
| 14 | `docs/adr/ADR-0001..0006` | Decisiones arquitectonicas |

---

## 5. Contratos y datos operativos (resumen)

- **Entrada principal:** `datos/direcciones.csv` (BOM+CRLF, `;`, columnas `parte1;parte2;ficha`, IDs posicionales D01..).
- **Ledger:** `datos/ledger.csv` (13 campos, upsert por id). Contiene registros de corridas reales previas con rutas de evidencia del entorno original (`dev\matriz-ibm-agent-piloto100\evidencia\...`) -- esas rutas pueden no existir en esta carpeta.
- **Control:** `datos/control.json` (si existe en runtime).
- **Credenciales 5250:** prioridad env vars `MATRIZ_5250_USUARIO`/`MATRIZ_5250_CLAVE` > `%USERPROFILE%\.matriz\creds.json` > `config/creds.json`. `config/` esta vacio en esta copia.
- **Jev/config IA:** `config/jev.json` no presente en esta copia; en `dev\matriz-ibm-agent-piloto100\config\jev.json` existia configuracion (revisar necesidad y seguridad de PII/exfiltracion antes de copiar).
- **Dependencia runtime:** `arranca.bat` invoca `..\mcp-anydesk\.venv\Scripts\python.exe` (proyecto hermano). Panel UI: `python tools/ui.py` (:8765 con token).

---

## 6. Hallazgos conocidos / riesgos para criticar (puntos de partida)

Estos provienen de documentacion y revision previa; la sesion critica debe validarlos contra el codigo/docs actuales:

1. **Doble pegado / idempotencia:** Riesgo de pegar dos veces o registrar estado inconsistente si hay reintento tras fallo parcial. Revisar guardias B3 y flujo pegado->ledger.
2. **Ledger sin lock / concurrencia:** Escritura de `ledger.csv` sin mecanismo de bloqueo explicito (hoy single-thread, pero fragil ante evolucion).
3. **Estados terminales y reanudacion:** Reanudacion "solo si coincide direccion" documentada; verificar robustez ante interrupciones (crash, timeout, cierre de ventana).
4. **OCR fragil y dependencia Jev:** Tesseract puede confundir caracteres (ej. 'o' acentuada -> '6'); Jev como segunda opinion con umbral 0.6. Revisar que datos/PII se envian a `_jev.py`/servicio externo.
5. **Pegador "a ciegas" / validacion de destino:** Riesgo de pegar en pestana/hoja incorrecta si el contexto de Chrome cambia. Contrato de columnas parcial.
6. **IDs posicionales (D01..):** Pueden inducir fichas cruzadas si la lista cambia; se menciona validacion por direccion parcial.
7. **Dependencia de AnyDesk y licencia:** Punto unico de fallo operativo y legal/licenciamiento.
8. **Perfiles de velocidad no garantizados:** Solo sigiloso se cumple consistentemente segun documentacion.
9. **Rutas absolutas en ledger historico:** Registros apuntan a evidencias del entorno original; no portables.
10. **Falta de repo git en entrega:** No hay historial de commits, tags ni CI en esta carpeta; dificulta trazabilidad y rollback.
11. **`config/` vacio vs expectativas:** Puede romper flujos si algun componente asume `config/jev.json` o `config/creds.json` presente.
12. **Modularizacion pendiente:** `loop.py` concentra logica; plan en `MODULARIZACION.md` no ejecutado (intencional por YAGNI, pero deuda si escala).

---

## 7. Que se espera de la sesion critica (entregables sugeridos)

1. **Diagnostico estructurado:** Fortalezas, debilidades, riesgos (seguridad, confiabilidad, operabilidad, mantenibilidad).
2. **Validacion documental:** Inconsistencias entre README, PLAN_VERSION_FINAL, GUIA_DE_USO, DISENO_FLUJO_DEFINITIVO, ESTADO_ORQUESTACION, etc.
3. **Revision de flujo y contratos:** Los contratos de datos/estado son suficientes y verificables? Hay huecos en B0-B7/P0-P5/E0-E3?
4. **Propuestas de mejora priorizadas:** Quick wins vs cambios estructurales, con criterio de impacto/riesgo/esfuerzo (sin ejecutar codigo).
5. **Checklist de "go/no-go" para produccion/operacion sostenida:** Que falta para considerar el sistema robusto.
6. **Preguntas abiertas para el operador:** Decisiones que requieren contexto humano/negocio (ej. git init, manejo de secretos, destino de evidencias).

**Restriccion explicita:** No ejecutar pruebas ni comandos que modifiquen estado operativo. Analisis estatico/documental unicamente.

---

## 8. Pendientes documentados preexistentes (para no perderlos)

- `T-IBM-05` (corrida real 5 direcciones) y `C-01` (cierre ciego) aparecen como **PENDIENTES** en `docs/engineering/EXECUTION_BATCHES.md`.
- Mejoras listadas en `docs/GUIA_DE_USO.md` (ej. deteccion de hoja/pestana, robustez OCR, cumplimiento de perfiles, etc.).
- Plan de modularizacion en `docs/MODULARIZACION.md` no ejecutado.

---

## 9. Notas finales

- Esta carpeta es la **copia de trabajo/entrega** para critica. La copia de respaldo bit-a-bit previa esta en `IBM AGENT - copia`.
- Si necesitas comparar con el origen de desarrollo, las referencias conocidas son `C:\Users\juanp_8h8f07l\dev\matriz-ibm-agent-piloto100` (piloto100), `dev\matriz-ibm-agent` (main), `dev\mcp-anydesk` (hermano runtime). **No asumas acceso a ellos desde esta sesion.**
- Cualquier propuesta de cambio debe respetar las reglas duras del proyecto: no tocar secretos, no romper puertas/semaforos, no duplicar funcionalidad existente sin justificacion (ver `TRACE_FUNCIONES.md`), y preferir cambios minimos completos (ponytail/YAGNI).
