# Diseño del flujo definitivo — corrida de 5 edificios sin paradas

Regla del operador (28/10): **pantalla negra o pantalla que no dice nada = la dejas vacía y sigues.**
El flujo no se detiene por una dirección: solo se detiene si no hay escritorio remoto.

---

## 0. Preparación (una vez por corrida)

| Paso | Qué hace | Si falla |
|---|---|---|
| P0 | Merge de `datos/fichas_pendientes.csv` en `datos/direcciones.csv` (fichas que no se pudieron guardar porque Excel tenía el CSV abierto) | aviso, sigue |
| P1 | Localiza AnyDesk por clase `ad_win*` | STOP (sin remoto no hay nada que hacer) |
| P2 | Reconecta si hay diálogo "Conexión finalizada" (`vigia --repetir`, espera 25 s) | 3 intentos → STOP |
| P3 | Login del 5250 si pide usuario (`login.hace_falta` + `entrar`) | 2 intentos → siguiente paso igual |
| P4 | Alt+Tab al 5250 si el remoto quedó en el navegador (`ir_al_5250`) | 4 intentos → sigue igual |
| P5 | Al formulario (`entrar_formulario`; Jev elige opción de menú si no se sabe) | 8 intentos → siguiente dirección |

## 1. Bloque por dirección (nunca lanza; siempre devuelve un estado)

```
para cada dirección pendiente:
    B0  reconectar / login / volver al 5250
    B1  estado de pantalla → formulario (si no, Jev; si no, ESC+F3 y reintento único)
    B2  macro de búsqueda + VERIFICAR el formulario por OCR
    B3  F10 → matriz de resultados (abajo)
    B4  listado → bloques de 15 filas (abajo)
    B5  volver al formulario
    B6  registrar en el ledger (append) y pasar a la siguiente
```

### B2 — verificación del formulario (lo que faltaba)

Después de escribir parte1 / parte2 / BOG / TVC, se lee el formulario por OCR y se compara:

| Caso | Acción |
|---|---|
| `Calle` == parte1 y `No.Casa` == parte2 (normalizado) | seguir a F10 |
| La fila contiene el valor esperado **más resto** (residuo del emulador, que no borra) | ESC, limpiar con 24 espacios, reescribir una vez; si repite → `revisar` y siguiente |
| El OCR no se puede leer | aviso en notas y seguir (no se bloquea por OCR dudoso) |

### B3 — matriz de resultados de F10 (ninguno detiene la corrida)

| Pantalla resultante | Significado | Acción | Estado final |
|---|---|---|---|
| `ficha` | el edificio existe | copiar la ficha del portapapeles → columna C del CSV → Shift+F4 | `ok` (sigue a B4) |
| `cuenta_matriz` | ya estamos en el listado | seguir a B4 | `ok` |
| `sin_coincidencia` | la dirección no está en el archivo | Escape | `no_encontrado` |
| `mensajes` y tras Intro vuelve al formulario | dirección inválida o inexistente | Intro ×2, Escape | `sin_datos` |
| `mensajes` y tras Intro sigue en mensajes | aviso encadenado | Intro ×1 más, Escape | `sin_datos` con el aviso en notas |
| `error` (aviso duro) | teclado inhibido | ESC → F3 → si vuelve al formulario | `sin_datos` |
| **pantalla negra / OCR casi vacío** | **no hay nada** | ESC, recapturar 2 veces; si sigue vacía, comprobar que AnyDesk sigue vivo (ventana `ad_win*` sin diálogo) | **`sin_datos`** si la ventana vive; **`revisar`** + reconectar si no vive |
| `desconectado` | se cortó AnyDesk | reconectar + login + reintento único | si repite → `revisar` |
| `None` sin señales | no se sabe qué es | Jev (`probabilities[choice] ≥ 0.6`); si no hay veredicto → ESC + F3 | `revisar` |

**Ningún caso aborta el lote.** El peor resultado de una dirección es `revisar` (queda anotado para el humano) y se pasa a la siguiente.

### B4 — listado, bloque a bloque

```
bloques = 0
mientras no fin_libro y bloques < MAX_PAGINAS (40, el valor real del codigo):
    si se alcanzan las 40 paginas → cerrar la direccion como `revisar`
    detectar cabecera Suscript
        no aparece → pantalla negra/no listado → ESC, recapturar, Jev decide
                     si no decide → cerrar dirección como `revisar`
    columna Suscript vacía (0 códigos y tinta < 40) → AvPág y seguir (no se copia)
    columna con tinta pero sin códigos → Jev: `vacia` / `con_datos` (umbral 0.6)
        con_datos → extraer igual, ajustando x para no clicar fuera de la columna
    con datos → 7 abajo (solo el primer bloque) → Shift+clic última celda Suscript
             → Ctrl+C → Alt+Tab → esperar destino con sondeo (hasta 3,6 s + reenvío)
             → Ctrl+Shift+V → verificar diff ≥ 3000 px (1 reintento)
             → Ctrl+Abajo + Abajo
             → registrar página en el ledger (`en_curso`, paginas_vistas=N)
    volver al 5250 (Alt+Tab con sondeo)
    AvPág → clasificar
        cuenta_matriz → siguiente bloque
        fin_libro → cerrar dirección `ok`
        desconectado → reconectar + login + reanudar en la página N+1
        negro/None → Jev; si no decide → AvPág otra vez (máx 2) → cerrar
```

### Reanudación — regla nueva y crítica

El id `D01..D05` es **posicional**: si el operador cambia una fila, el id apunta a otra dirección.
Por eso la reanudación **solo se aplica si la dirección del ledger coincide** con la del archivo:

```
si ledger[id].estado == "en_curso" y ledger[id].parte1 == direccion.parte1
   y ledger[id].parte2 == direccion.parte2:
        reanudar en paginas_vistas + 1   (AvPág × paginas_vistas)
si no: empezar de cero (ignorar el en_curso viejo)
```

Sin esta comprobación, D02 (`CR 103D/86-55`, ya en el ledger) se habría reanudado en la
página 2 del edificio **equivocado**: se habría saltado la página 1 de `CR 84A/145-94`.

## 2. Dónde decide Jev (y dónde no)

| Punto | Pregunta a Jev | Umbral | Si no hay veredicto |
|---|---|---|---|
| Pantalla desconocida | ¿qué pantalla es? (7 estados) | `probabilities[choice] ≥ 0.6` | ESC + F3 → reintento → `revisar` |
| Menú numerado | ¿qué opción abre CONSULTA EDIFICIO-CUENTA MATRIZ? | 0.6 | se prueban las opciones seguras en orden |
| Columna Suscript con tinta pero sin códigos | ¿vacía o con datos? | 0.6 | se asume **con datos** (nunca se pierde información) |
| Ficha vs mensaje de programa | ¿es una ficha de edificio? | 0.6 | se trata como mensaje (`sin_datos`) |

Jev **nunca** toca el ratón ni el teclado: solo devuelve una etiqueta. Toda acción la ejecuta
el código con teclas y clics ya validados (`press_keys`, `click_point`, `paste_clipboard`).
Las opciones peligrosas (Finalizar / Salir / Cerrar / Terminar / Abandonar) se filtran antes
de ofrecérselas.

## 3. Cuándo SÍ se detiene la corrida

1. No aparece la ventana de AnyDesk.
2. La reconexión falla 3 veces seguidas.
3. El panel de control (`tools/ui.py`, `datos/control.json`) recibe DETENER.
4. Las 5 direcciones terminan en `revisar` (no tiene sentido insistir).

Cualquier otra cosa se anota y se sigue.

## 4. Salidas de la corrida

| Salida | Dónde |
|---|---|
| Bloques pegados en la hoja | Google Sheets `LIMPIEZA RR` → pestaña `temp borrador` |
| Ficha de cada edificio (cuenta, nombre, dirección) | columna C de `datos/direcciones.csv`; si Excel la bloquea → `datos/fichas_pendientes.csv` |
| Estado por dirección | `datos/ledger.csv` (append-only; última fila por id manda) |
| Traza del semáforo | `datos/traza.jsonl` + `datos/traza.md` |
| Evidencia | `evidencia/*.png` (ciclo-antes, cp-listo, página) |
| Dossier | `tools/verifications/autonomo-<ts>.md` |

Estados finales por dirección: `ok` (páginas pegadas), `no_encontrado` (la dirección no está en
el archivo del 5250), `sin_datos` (pantalla sin contenido: se deja vacía y se sigue),
`revisar` (no se pudo resolver), `en_curso` (corte a media matriz, reanudable).

## 5. Los 5 registros actuales

| id | parte1 | parte2 | observación |
|---|---|---|---|
| D01 | CR 17B | 175-77 | **decisión del operador antes de lanzar**: ya se pegó el 27/10 (10 páginas, 150 filas). Opción A: marcarlo `ok` en el ledger y saltarlo (la hoja conserva lo del 27/10). Opción B: repetirlo, pero primero hay que borrar el bloque viejo de la hoja o quedará duplicado |
| D02 | CR 84A | 145-94 | nueva (sustituye a `CR 103D/86-55`, que daba error del programa TCCEDFRO) |
| D03 | CR 54A | 149-29 | nueva |
| D04 | CL 150A | 96A-40 | nueva |
| D05 | CR 147 | 145-40 | nueva |

Antes de lanzar hay que borrar de la hoja el bloque duplicado de D03 viejo (filas 51-65 de
`temp borrador`): es dato de otra corrida, no de estos 5 edificios.
