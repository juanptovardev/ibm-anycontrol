# ADR-0002 — Reglas deterministas antes que Jev

- **Fecha**: 2026-10-27
- **Estado**: Aceptada
- **Ámbito**: `dev/matriz-ibm-agent`

## Contexto
El proyecto se pidió con "Jev como motor de lectura en pantalla". Jev
(`jev-1.13-free`) es un modelo de **decisiones tipadas sobre texto**: recibe
`instructions` + `criteria` y devuelve `noul` / `choice` / `score`. **No ve
imágenes**: no puede recibir la captura ni "mirar" la pantalla. Además la cuota
del modelo free devuelve 429 con facilidad.

## Decisión
La arquitectura real es en tres capas, en este orden:
1. **Tesseract local** (psm 6, x1, sin reescalar) → texto de la captura 1:1.
2. **Reglas puras** (`estado.reglas`) → clasificación determinista en <5 ms.
3. **Jev solo si la regla duda** (~300 ms). Si su confianza < 0.6 → `estado=None`
   + error explícito: "no pude clasificar", nunca "la pantalla está mal".

## Consecuencias
- Positivo: la velocidad del ciclo no depende de una red ni de un modelo.
- Positivo: el fallo de Jev degrada a "no clasifico" en vez de "clasifico mal".
- Positivo: el motor es testeable sin pantalla (lógica pura separada de E/S).
- Negativo: hay que mantener las reglas a mano cuando el IBM cambia sus
  mensajes; el coste es una lista corta de señales documentada.
- Negativo: Jev queda como segunda opinión; su valor es cuando el texto es
  ambiguo de verdad, no como ruta caliente.
