# ADR-0001 — Macro 5250 determinista en vez de navegación por OCR

- **Fecha**: 2026-10-27
- **Estado**: Aceptada
- **Ámbito**: `dev/matriz-ibm-agent`

## Contexto
La consulta dedirecciones del emulador IBM 5250 tiene un recorrido estable:
formulario → F10 (Buscar Dirección) → ficha del edificio → Shift+F4 → listado de
unidades con suscriptores. La alternativa "el agente decide a dónde hacer clic
leyendo la pantalla con OCR" parece más flexible, pero cada decisión por OCR
introduce una fuente de error (una cifra mal leída = un clic en la fila
equivocada = datos en la columna equivocada).

## Decisión
Se congela una **macro determinista** que ejecuta el recorrido con un número
mínimo de pasos y con verificación posterior:
`clic (doble) en celda 1 de Calle → flecha derecha → flecha izquierda → parte1 →
+ (numpad) → parte2 → + (numpad) → F10 → Shift+F4`.

La lectura (OCR) se usa para **verificar** el resultado, nunca para elegir el
siguio paso dentro de la macro.

## Consecuencias
- Positivo: comportamiento repetible, auditable y rápido (≈1 s la macro).
- Positivo: si el texto cae en el campo equivocado, se detecta por tinta de
  píxeles **antes** de pulsar F10 (blindaje B2) y se aborta, en vez de propagar
  basura.
- Negativo: si la pantalla remota no es el formulario esperado, la macro no
  aplica → por eso B1 exige clasificar el estado antes de teclear.
- Negativo: variantes del IBM (otros skin) requerirían otro macro; hoy solo
  existe un formulario verificado.
