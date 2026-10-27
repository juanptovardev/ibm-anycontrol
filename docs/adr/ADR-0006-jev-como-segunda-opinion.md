# ADR-0006 — Jev como segunda opinión + modo de aprobación manual

- **Fecha**: 2026-10-27
- **Estado**: Aceptada
- **Ámbito**: `dev/matriz-ibm-agent` + `dev/jev-gate`

## Contexto
Tres llaves de OpenCode fallaron seguidas (free 429 por cuota, pagadas 401
`api_key_expired`). La llave viva está en
`%LOCALAPPDATA%\opencode\auth.json` (providers `opencode` / `opencode-go`,
misma clave `oc_sk_…`), y `jev-1.13-free` responde 200 con `cost 0`;
`jev-1.13` (pago) devuelve **403 "Model access is disabled"** en esta cuenta.
Por tanto la cuota free es el punto de falla real.

## Decisión
1. El motor **no depende** de Jev para funcionar: las reglas deterministas son
   el gate; Jev es segunda opinión y se degrada a "no clasifico" si falla.
2. Mientras la cuota no sea confiable, el gate de **acciones irreversibles**
   (escritura en pantalla, pegado en la hoja) es la **aprobación del humano**:
   el agente propone, el operador valida. El ledger registra `aprobado_por`.
3. La clave se lee de `auth.json` en runtime y viaja en un archivo temporal de
   `curl` (nunca en argv ni en logs).
4. `dev/jev-gate` queda como servidor MCP para consumo externo; su `.env` no
   se versiona (`.gitignore` con `.env`).

## Consecuencias
- Positivo: 429 de Jev no detiene el ciclo; solo degrada la segunda opinión.
- Positivo: el flujo sigue siendo auditable (quién aprobó qué, cuándo).
- Negativo: en E1/E2 el humano aprueba cada inyección → el ahorro de tiempo
  real empieza en E2, cuando el pegado es determinista y reversible por ledger.
- Negativo: la clave vive en un archivo del usuario: si se rota, hay que
  re-extraerla (sin tocar código).
