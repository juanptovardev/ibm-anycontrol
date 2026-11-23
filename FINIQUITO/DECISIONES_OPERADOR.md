# Decisiones del operador — Finiquito IBM AGENT

Fecha: 2026-11-18
Base: instrucción del operador “Procede hasta terminar en autonomo”.
Alcance: estas decisiones resuelven D-01..D-07 del `PLAN_DE_FINIQUITO.md` con la opción más segura y reversible. Cualquier cambio de política posterior requiere aprobación explícita.

| ID | Decisión | Resolución | Motivo |
|---|---|---|---|
| D-01 | Jev (tercero) | **OFF por defecto.** Sin clave dedicada, `disponible()` = `False`. Se elimina el fallback a la credencial personal de OpenCode. Se puede activar solo con `MATRIZ_JEV=1` + clave dedicada + DPA. | Evita enviar OCR con direcciones/suscriptores a un tercero y evita usar una credencial personal. |
| D-02 | Versionar datos | **No.** `datos/` y `config/*.json` quedan fuera de git. El baseline y los rollbacks son ZIP + SHA256. | Los CSV contienen PII operativa. |
| D-03 | Panel UI | **Solo `127.0.0.1` por defecto.** LAN solo con `MATRIZ_UI_BIND` explícito y aviso. | Reduce superficie de ataque del panel. |
| D-04 | Git local | **Diferido.** No se inicializa git en este finiquito; se usan snapshots ZIP por WP. G0-07 queda `[-]`. | Evita commitear PII antes de que WP-06 ajuste `.gitignore`. |
| D-05 | Ventana | Sesión actual, sin tráfico de producción. AnyDesk/Excel cerrados por el operador. | No hay ventana formal; se trabaja sobre copia y datos respaldados. |
| D-06 | Revisor ciego | **Subagente `code-reviewer` con contexto limpio** en Gate 3; la firma humana final queda como reserva. | Nadie debe calificar su propio trabajo; el subagente no participó en la implementación. |
| D-07 | Waivers | **Sin waivers S1.** Solo se aceptan reservas P1/P2 por dependencias externas (repo `mcp-anydesk`, AnyDesk/5250, revisor humano), documentadas en el dossier. | Un S1 abierto impide el cierre. |

## Consecuencias operativas

- WP-02 implementa D-01.
- WP-05 implementa D-03.
- WP-06 implementa D-02.
- G0-07 no se ejecuta; el ZIP de WP-00 es el baseline.
- Gate 3 incluye revisión por subagente; la aprobación humana final se registra como reserva si no está disponible.
