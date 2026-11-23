> **Snapshot 2026-11-19.** Plan de mejoras de esa fecha. Lo implementado está en ESTADO_ORQUESTACION.

# PLAN DEFINITIVO MEJORAS - IBM AGENT Enterprise Ultimate

## Visión General
Proyecto: Optimización y consolidación del agente IBM 5250 a versión enterprise ultimate.
Objetivo: Consolidar mejoras estructurales, limpieza segura y handoff para sesión nueva sin contexto.
Metodología: ORCA (Operación -> MERGE -> AUDIT -> CIERRE), senior SWE principles, ponytail (YAGNI), EGM skills.

## 1. Estado Actual Verificado
- **Ruta destino:** C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT
- **Copia de seguridad:** IBM AGENT - copia (126 archivos, 9 directorios, intacto)
- **No es repo git:** Se documenta estado actual; decisión de inicializar git pendiente.
- **Config vacío:** config/ intencional; credenciales via env vars o %USERPROFILE%\.matriz\creds.json.
- **Procesos:** Ninguno activo; rranca.bat usa venv hermano mcp-anydesk.
- **Total archivos:** 126 (9 directorios), sin __pycache__, *.log, *.err, *.tmp, backups, prueba_*, evidencia/, _experimentos/.

## 2. Mejoras Prioritarias (Orden por impacto)

### 2.1 Consolidación de dependencias y credenciales
- **Objetivo:** Asegurar flujo de credenciales robusto en IBM AGENT.
- **Acción:** Documentar y validar orden de prioridad:
  1. Variables de entorno MATRIZ_5250_USUARIO / MATRIZ_5250_CLAVE
  2. %USERPROFILE%\.matriz\creds.json
  3. config/creds.json (fallback portátil - actualmente vacío)
- **Evidencia:** 	ools/credenciales.py ya implementa esta lógica; solo falta documento explícito.

### 2.2 Modularización asistida (sin tocar loop.py)
- **Objetivo:** Extraer funciones puras de 	ools/loop.py a módulos independientes.
- **Acción (ponytail/YAGNI):** Solo si se necesita nuevo comportamiento; no mover puertas existentes.
- **Evidencia:** MODULARIZACION.md ya describe el plan; pendiente ejecución si requiere nueva feature.

### 2.3 Mejora de OCR y detección de señales
- **Objetivo:** Reducir falsos positivos en lectura de pantalla IBM 5250.
- **Acción:** Revisar TRAZA_Y_SEMAFORO.md y DISENO_FLUJO_DEFINITIVO.md umbrales Jev; mantener probabilities>=0.6 como guardia.
- **Evidencia:** PERFILES_VELOCIDAD.md ya mide tiempos; optimizaciones A/C/D hechas.

### 2.4 Blindaje y puertas E0-E3
- **Objetivo:** Evitar doble pegado, estados terminales inconsistentes, exfiltración PII.
- **Acción:** Reglas ya definidas en ESCALAMIENTO.md (B1-B8) y DISENO_FLUJO_DEFINITIVO.md (B0-B7).
- **Pendiente:** Validar que ledger.csv no acepte filas duplicadas sin lock; agregar write-ahead si es necesario.

### 2.5 Hand-off y documentación para crítica externa
- **Objetivo:** Entregar proyecto a sesión nueva que critique y analice sin ningún contexto previo.
- **Acción:** Crear HANDOFF_CRITICA_SESION_NUEVA.md con todos los datos, árbol de archivos, y estado actual.
- **Evidencia:** Documento en preparación.

## 3. Estructura de Entrega para Nueva Sesión
El proyecto queda en C:\Users\juanp_8h8f07l\OneDrive\Desktop\Proyectos\IBM AGENT listo para que una nueva sesión:
1. Lea HANDOFF_CRITICA_SESION_NUEVA.md para entender el objetivo y estado.
2. Revise el árbol de archivos (ver anexo).
3. Proponga mejoras sin necesidad de ejecutar nada.
4. No ejecute pruebas; solo evidencia y sugerencias.

## 4. Riesgos Conocidos y Deuda Técnica
- **Doble pegado:** Documentado en GUIA_DE_USO.md y DISENO_FLUJO_DEFINITIVO.md; guardia B3.
- **OCR frágil:** jev como segunda opinión; threshold 0.6.
- **Licencia AnyDesk:** Validar disponibilidad antes de corridas extensas.
- **Single-thread:** Límite de concurrencia; optimizaciones en PERFILES_VELOCIDAD.md.
- **Ledger sin lock:** Riesgo de race condition en escritura concurrente (aunque single-thread hoy).
- **Exfiltración PII via Jev:** _jev.py envía contexto a servicio externo; revisar qué datos se incluyen.

## 5. Siguientes Pasos (para esta sesión)
1. Consolidar HANDOFF_CRITICA_SESION_NUEVA.md.
2. Añadir sección de handoff al ESTADO_ORQUESTACION.md (append-only).
3. Verificar que config/ vacío no rompe flujo; documentar rutas alternas de credenciales.
4. Finalizar y guardar. No correr pruebas.
