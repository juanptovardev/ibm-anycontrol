# ADR-0008 — Jev apagado por defecto y datos personales en el OCR

- **Fecha**: 2026-11-19
- **Estado**: Propuesto
- **Relacionado**: ADR-0002 (reglas antes de Jev), ADR-0006 (Jev como segunda opinión)
- **Ámbito**: `tools/_jev.py`, `docs/PRIVACY.md`

## Contexto
Jev era una segunda opinión por LLM sobre pantallas ambiguas. Dos problemas:
1. La versión anterior tomaba la clave de `%LOCALAPPDATA%\opencode\auth.json`
   (credencial personal del operador), fuera del alcance del proyecto.
2. El texto de la pantalla 5250 lleva nombres y direcciones de suscriptores
   (datos personales). Enviarlo a un endpoint externo es una decisión con
   implicaciones de privacidad, no una mejora técnica.

## Decisión propuesta
- Jev queda **apagado por defecto**: `MATRIZ_JEV=0`; `disponible()` devuelve
  `False` sin una clave dedicada.
- No reutiliza `auth.json` ni la credencial personal de OpenCode. La clave, si se
  activa, se lee de `MATRIZ_JEV` con `MATRIZ_JEV_KEY` o `config/jev.json`.
- Cuando está activo, solo decide entre pantallas ambiguas con `probabilities`
  ≥ 0,6 y nunca toca ratón ni teclado.
- El tratamiento de datos personales se documenta en `docs/PRIVACY.md`: base legal,
  DPA del proveedor del endpoint y retención.

## Consecuencias
- Positivo: el flujo funciona sin dependencia externa; ninguna pantalla envía PII
  por defecto.
- Negativo: las pantallas ambiguas se resuelven con las reglas de ADR-0002, sin
  segunda opinión.
- Pendiente: activar Jev con datos reales exige la aprobación de privacidad (estado
  Propuesto, no Aceptada).
