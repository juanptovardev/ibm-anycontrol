# Plan de la versión final — Agente 5250

> Documento de trabajo. Todo lo que aquí está **medido** lleva la cifra; lo que es
> hipótesis está marcado como tal. Fecha de corte: 2026-11-03.

## 0. Qué es esta versión

Un agente que, dada una lista de direcciones, entra al 5250, busca cada edificio,
copia la ficha del edificio a un CSV, extrae la lista de suscriptores página a
página y lo pega en Google Sheets, sin que nadie toque el teclado.

La versión que se razonó tiene tres capas:

1. **Motor** — la lógica determinista (regras, OCR, teclas, portapapeles).
2. **Perfiles** — el ritmo con el que se ejecuta (4 niveles).
3. **Orquestación** — el supervisor que relanza, reanuda y cierra solo.

## 1. Estado verificado (03/11/2026)

Corrida completa sobre las **121 direcciones reales** del piloto:

| Métrica                    | Resultado                             |
| -------------------------- | ------------------------------------- |
| Direcciones                | **121 / 121** (ninguna fuera)             |
| Completadas                | **111 ok**                                |
| No existen en el 5250      | 10 (`no_encontrado`, columna 3 vacía)   |
| Errores / Halt             | **0 / 0**                                 |
| Páginas pegadas            | **134**                                   |
| **Filas pegadas**              | **1.710**                                 |
| Fin de archivo automático  | **111 / 111 (100%)**                      |
| Ritmo real                 | **24 – 25 s / dirección**                |
| Tasa de éxito              | 91,7 % de las direcciones procesadas     |

Cortes de AnyDesk por licencia: cortes y se recuperó **solo** (reconexión + login
del 5250 + reanudación en la página exacta).

## 2. Los 4 perfiles (`tools/perfil.py`)

Un perfil es un **techo** por dirección, no un objetivo: el motor mide su tiempo
real y reparte el sobrante en 4 pausas naturales (antes del F10, tras la ficha,
entre páginas, al cerrar) con jitter. Si el motor no llega al techo, el informe
lo dice en vez de fingir.

| #   | Perfil    | Techo s/dir | Real medido | ¿Se cumple? | Tu día (1.180 dir) |
| --- | --------- | ----------- | ----------- | ------------ | ------------------ |
| 1   | Sigiloso  | 27,5        | 24 – 25     | **sí**       | 9,0 h             |
| 2   | Humano    | 18,3        | 24 – 25     | no           | 6,0 h             |
| 3   | Rápido    | 12,2        | 24 – 25     | no           | 4,0 h             |
| 4   | Psicópata | 9,15        | —           | **imposible** | 3,0 h             |

- **Techo real medido del motor: 24 s/dirección** → tu día son **7,9 h**, no 6.
- **Psicópata es inalcanzable**: el suelo son ~12,6 s (el `Alt+Tab` tarda 1–3 s en
  llegar al remoto y el portapapeles remoto no se puede leer). Ver T5.

**La cadencia de teclas NO va atada al perfil.** Con 120 ms × 93 teclas el propio
perfil Sigiloso se pasa de su techo. La "humanidad" viene del jitter y de las
pausas, no de teclear lento. La cadencia es un knob global aparte
(`--teclas=rapido|humano`, 35 / 110 ms).

## 3. Reparto del tiempo (medido, página de 9 s antes de optimizar)

| Componente                    | ms    | %   |
| ----------------------------- | ----- | --- |
| Esperas fijas (`sleep`)       | 3.700 | 41% |
| OCR (3 pasadas por página)    | 2.500 | 28% |
| Teclas + latencia MCP/AnyDesk | 2.200 | 25% |
| Capturas + PNG                | 370   | 4%  |
| `sel_box` (informativo)       | 180   | 2%  |

Coste unitario real de la máquina: OCR de pantalla 932 ms · franja 330 ms ·
`clasificar_rapido` 405 ms · `PrintWindow` 30 ms · PNG 31 ms · `sel_box` 178 ms ·
tinta 8 ms · diff 10 ms.

## 4. Optimizaciones: qué está hecho y qué falta

| Id   | Mejora                                   | Ahorro      | Estado            |
| ---- | ---------------------------------------- | ----------- | ----------------- |
| A    | Esperas fijas → verificación activa      | ~1,3 s/pág. | **hecho**         |
| B    | Recorte del OCR de clasificación          | ~1,2 s/pág. | pendiente         |
| C    | Capturas: solo las que aportan prueba     | ~250 ms/pág. | parcial           |
| D    | Fusión de teclas contiguas (15 → 9)       | ~0,9 s/dir  | **hecho**         |
| E1   | Clasificador por píxeles (20 ms vs 405)   | ~0,8 s/pág. | **hecho** (capa B)|
| E2   | Cachear la cabecera `Suscript` por edificio| ~1,1 s/pág.| pendiente         |
| E3   | Fusión de teclas del bloque (93 → ~60)    | ~1,2 s/pág. | pendiente         |
| E4   | Sacar `sel_box` del camino caliente        | 180 ms/pág. | pendiente         |

- **A**: `cp._espera_pegado` sondea el diff cada 120 ms en vez de dormir 0,6 s;
  los sleeps del bloque y del copiado bajados.
- **D**: la búsqueda fusiona `right+left+delete` en una sola llamada por campo
  (`nombre_sentar`, `calle_sentar`): de 15 a 9 llamadas MCP.
- **E1**: el 5250 es 79,7–82,2 % de píxeles casi negros y la hoja de Chrome
  79,0–82,7 % casi blancos, medido sobre **228 capturas reales**. Los dos grupos
  no se solapan → margen de 4×. Sustituye al OCR en el sondeo del destino.
- **B NO se aplicó** (y no a ciegas): la ficha del edificio se detecta por
  "OTRAS DIRECCIONES / TOTAL UNIDADES" a media altura; si se recorta la franja
  de clasificación, la ficha se confunde con el formulario. Queda pendiente
  medir una banda que cubra ambos casos.

## 5. Tareas priorizadas

### T1 — Portar `piloto100` a `master` (riesgo: nulo)
Todo lo que hoy solo existe en la rama `piloto100`: los fixes de
`sin_coincidencia`, los perfiles, las optimizaciones, la capa B, el fix del
`Ctrl+Abajo`, el supervisor, el separador y el reset.
**Criterio**: `master` == `piloto100` en el mismo commit y la suite verde.

### T2 — Modularización 0.3 (riesgo: medio, red: 279 tests)
El sistema hoy son 4 archivos grandes con responsabilidades mezcladas. Objetivo:
cuatro módulos con una responsabilidad cada uno, y `loop.py` como fachada.

| Módulo            | Responsabilidad                                        |
| ----------------- | ------------------------------------------------------ |
| `matriz_buscar`   | Limpiar el formulario, escribir calle/casa/BOG/TVC, F10 |
| `matriz_ficha`    | Copiar la cabecera del edificio, volcarla al CSV        |
| `matriz_extraer`  | Shift+clic, copiar, pegar, posicionar, paginar         |
| `orquesta`        | Director: política, luces, ledger, reanudación          |

**Criterio**: los 279 tests siguen verdes sin reescribir la lógica (se **extrae**,
no se rehace) y `tools/loop.py` baja de ~995 líneas.

### T3 — Contrato de columnas de la hoja (riesgo: medio)
Hoy se pega "donde quedó el cursor". El contrato debe:
1. Leer la fila 1 de la hoja y deducir el mapa (DIRECCIÓN / EDIFICIO / SUSCRIPTOR).
2. Hacer **un** clic en la celda destino antes de pegar.
3. Cabecera inesperada → **error explícito**, no pegar a ciegas.
**Criterio**: con la hoja vacía y con cabecera cambiada, el agente dice qué espera
y qué encontró, y no pega nada.

### T4 — E2: cachear la cabecera `Suscript` (riesgo: bajo)
La cabecera del listado está en el mismo píxel dentro del mismo edificio. Se
cachea por edificio y solo se cuentan suscriptores por píxeles (8 ms).
**Criterio**: en la 2ª página de un edificio no se ejecuta OCR de pantalla
completa; el conteo de suscriptores sigue siendo correcto.

### T5 — Modo "lado a lado": quitar el `Alt+Tab` (riesgo: medio, **es la palanca de las 6 h**)
El `Alt+Tab` cuesta 1–3 s por cada ida y vuelta (2–6 s por página) y es la
causa número uno de fallos intermitentes. Si el 5250 y Chrome quedan **visibles a
la vez** en el escritorio remoto, se sustituye por un clic directo.
**Requiere**: que el operador deje el remoto en esa disposición (una vez).
**Criterio**: con el modo lado a lado, una dirección baja de 24 s a ≤19 s.

### T6 — E3/E4: más fusión de teclas y fuera `sel_box` (riesgo: bajo)
**Criterio**: el bloque baja de 9 s a ≤6,5 s.

### T7 — Fiabilidad: tope de reintentos y detección de atasco
Un `error` se reintenta en cada vuelta del supervisor (hasta 8). Con tope por
dirección y detección de N fallos seguidos, el supervisor para y avisa en vez de
insistir.
**Criterio**: 3 direcciones con el mismo fallo → el supervisor para y lo dice.

## 6. Lo que se descarta (decidido)

- **Verificación post-pegado por contenido**: la pidió la calidad de datos, pero
  el operador la descartó por coste de tiempo. Se conserva solo la verificación
  de que *cambió* la hoja (diff), no de que el contenido sea el correcto.
- **Perfil psicópata**: no es un problema de código, es un problema de física
  (latencia del escritorio remoto).
- **Evadir controles del firewall o del AS/400**: no se hace. Lo que sí se
  controla es el **ritmo**, que es lo que hace que la huella no sea identificable
  como máquina (un humano a 18,3 s/dirección es indistinguible de un bot a 24 s;
  un bot a 9 s no lo es).

## 7. Riesgos vivos

| Riesgo                                            | Impacto | Mitigación                                   |
| ------------------------------------------------- | ------- | -------------------------------------------- |
| Ids posicionales (D01..D121)                      | alto    | El ledger compara la dirección antes de reanudar. Un cambio de fila en el CSV invalida el punto: se rehace. |
| El foco local roba el primer plano a AnyDesk      | alto    | `enfocar` + `ALT` ficticio antes de cada inyección; nunca ejecutar nada en primer plano durante una corrida. |
| Licencia de AnyDesk corta la sesión cada ~10 min  | medio   | Reconexión + login + reanudación automáticos (probado). |
| Excel abierto bloquea el CSV                      | medio   | 3 reintentos y volcado a `datos/fichas_pendientes.csv` con la dirección para validar al recuperar. |
| El 5250 no borra y `home` salta al primer campo   | medio   | La limpieza usa la secuencia del operador (clic → der → izq → Suprimir → `+`). |
| El humano usa el escritorio remoto               | medio   | Detener si hay actividad de ratón; nunca competir por el foco. |
| Un bloque de 1 línea rompe el `Ctrl+Abajo`        | **resuelto** | Se cuenta las líneas con datos; con 1 sola se usa solo `Abajo`. |

## 8. Orden de ejecución

1. **T1** — portar a `master` (deja el código bueno donde se trabaja).
2. **T2** — modularizar (con la suite como red).
3. **T3** — contrato de columnas (define el destino del pegado).
4. **T4** — cache de cabecera.
5. **T5** — modo lado a lado (requiere al operador).
6. **T6/T7** — afinado de velocidad y de reinsistencia.

Cada tarea se cierra con la suite en verde y una entrada en
`docs/engineering/ESTADO_ORQUESTACION.md`.
