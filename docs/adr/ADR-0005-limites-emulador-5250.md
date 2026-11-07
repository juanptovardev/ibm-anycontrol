# ADR-0005 — Límites del emulador 5250 (no delete, no home, numpad-add, shift-F4)

- **Fecha**: 2026-10-27
- **Estado**: Aceptada
- **Ámbito**: `dev/matriz-ibm-agent`

## Contexto
El emulador IBM 5250 que corre en el PC remoto tiene comportamientos no
estándar que costaron varias rondas de pruebas:

| Tecla | Comportamiento real | Consecuencia |
|-------|---------------------|--------------|
| `delete` | **no borra** (el texto se acumula: `175-` → `175-175-7`) | Prohibido borrar; solo escribir en campo limpio |
| `home` | **no va al inicio del campo**: salta al primer campo del registro (Nombre) | Prohibido usar `home`; de ahí venía la mayoría de los "textos en Nombre" |
| `+` alfanumérico | no avanza de campo | El avance es `add` del **bloque numérico** |
| `F4` suelto | **cierra** la ventana del emulador | `F4` siempre con `shift`; el código de `press_keys` lo bloquea |
| `Enter` | prohibido por el transporte MCP y por el 5250 en modo consulta | Nunca se inyecta |

Además, tras un clic el cursor no queda "sentado" en el campo: hay que pulsar
`flecha derecha` + `flecha izquierda` (truco validado por el operador) o el
emulador queda inhibido ("área protegida", indicador `A X II`).

## Decisión
Se prohíben `delete` y `home` en los flujos del formulario. La macro usa solo:
doble clic en la celda 1 → `right` → `left` → escribir → `add` → escribir → `add`
→ `F10` → `shift+f4`.

## Consecuencias
- Positivo: el flujo es **idempotente por diseño**: no borra nada, no depende de
  la posición previa del cursor dentro del campo.
- Positivo: se eliminó de raíz la clase de fallos "el texto quedó a mitad de
  campo" (la causa de los `CR 1` truncados).
- Negativo: no se puede corregir un campo ya escrito por la macro → hay que
  recargar el formulario (operador) y repetir el item (blindaje B5, 1 reintento).
- Negativo: si el 5250 cambia de versión, estos límites hay que re-verificar.
