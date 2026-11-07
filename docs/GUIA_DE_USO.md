# Guía de uso, modos, mejoras y críticas

Documento único de operación. Escrito el 03/11/2026 tras la corrida completa
de 121 direcciones y la validación del cambio de ventana por taskbar.

---

## 1. Balance

### Qué hace el sistema

Lee direcciones de un CSV, las escribe en el emulador 5250 de la oficina a
través de AnyDesk, copia el listado de suscriptores de cada edificio y lo pega
en la hoja `LIMPIEZA RR` de Google Sheets, dejando el cursor listo para el
siguiente bloque.

### Números medidos (no estimados)

| Métrica | Valor |
| --- | --- |
| Corrida más grande | **121 direcciones** |
| Completadas | 111 `ok` |
| No existen en el 5250 | 10 `no_encontrado` |
| Errores / abortes | **0 / 0** |
| Páginas pegadas | 134 |
| **Filas pegadas** | **1.710** |
| Fin de archivo detectado solo | 111/111 |
| Ritmo con el cambio por taskbar | **20,4 s/dirección** |
| Ritmo con `Alt+Tab` (antes) | 24–25 s/dirección |
| Ritmo del operador a mano | 18,3 s/dirección |

### Qué se ha construido

- **Motor 5250**: entrada al formulario, búsqueda por calle y número, ficha
  del edificio, listado de unidades, paginación y detección de fin de archivo.
- **Pegado**: Shift+clic en la última celda de Suscript, Ctrl+C, cambio de
  ventana, Ctrl+Shift+V, reposicionamiento del cursor.
- **Cambio de ventana por icono de taskbar**: el `Alt+Tab` dejó de llegar al
  remoto; ahora se hace clic en el icono de Chrome o del emulador.
- **Supervisor**: relanza el lote solo, con watchdog, tope de reintentos por
  dirección y reintento tras corte de licencia de AnyDesk.
- **4 perfiles de velocidad** (techos, no promesas).
- **Re-login automático** del 5250 con credenciales fuera del repo.
- **Contrato de columnas**: comprueba que la hoja tiene DIRECCION, EDIFICIO y
  SUSCRIPTOR antes de pegar.
- **Ledger como tabla**: una fila por dirección, con reanudación por página.

---

## 2. Guía de uso

### Preparar el entorno (una vez por sesión)

1. AnyDesk conectado a la oficina.
2. El emulador 5250 abierto y logueado (si se cae, el agente reloguea solo).
3. Chrome con la hoja `LIMPIEZA RR`, pestaña `temp borrador`, cursor en la
   primera celda vacía de la columna A.
4. **Excel cerrado** (si está abierto, las fichas van a `fichas_pendientes.csv`).

### Añadir direcciones

```
python tools\anexar_direcciones.py nuevas.txt
```

- Añade **al final** sin tocar las existentes ni sus fichas.
- Deduplica: si repites una, la cuenta como `repetidas` y no la escribe.
- Hace backup antes de escribir.
- Acepta `--dry` para ver qué haría sin escribir.
- Acepta `--portapapeles` (pegas la lista y listo).

No usar `separar.py` sobre producción: sobrescribe el archivo. Si lo necesitas,
`separar.py` escribe ahora en `datos/direcciones_nuevas.csv` por defecto y para
tocar producción exige `--produccion` (y no degrada: si las filas nuevas son
menos que las actuales, se niega).

### Lanzar el lote

```
python tools\supervisor.py --perfil=psicopata --teclas=rapido
```

Variantes:

```
python tools\supervisor.py --ids=D126,D127,D128         # solo algunas
python tools\supervisor.py --perfil=humano --teclas=humano
python tools\supervisor.py --max-vueltas=3 --horas=4
```

El supervisor deja:
- `datos/supervisor.json` — estado vivo (vuelta, pendientes, congelados).
- `datos/supervisor-vuelta-N.log` — log de cada vuelta.
- `datos/supervisor.lock` — candado; si el proceso muere de golpe hay que
  borrarlo a mano.

### Comandos de diagnóstico

| Comando | Para qué |
| --- | --- |
| `python tools\sonda.py` | Dice si la pantalla es el 5250 o el navegador, y guarda un PNG |
| `python tools\estado.py <hwnd>` | Estado clasificado + OCR |
| `python tools\vigia.py <hwnd> --repetir` | Pulsa «Repetir» del corte de licencia |
| `python tools\credenciales.py` | Dice si hay credenciales (nunca muestra la clave) |
| `python tools\reset_ledger.py --desde=D105` | Rehace desde una dirección |
| `python tools\registrar_pegado.py D01=1` | Registra a mano una página ya pegada |
| `python tools\ui.py` | Panel de control en http://127.0.0.1:8765 |
| `python -m unittest discover -s tests` | Suite (345 tests) |

### Parar

- **Panel** (`ui.py`): botón DETENER.
- **Sin panel**: mata el proceso y borra `datos/supervisor.lock`.

---

## 3. Modos

### Perfiles de velocidad (techos por dirección)

| Perfil | Techo | Tu día (1.180 dir) | Leads en 6 h | ¿Se cumple hoy? |
| --- | --- | --- | --- | --- |
| `sigiloso` | 27,5 s | 9,0 h | ~3.000 | Sí |
| `humano` | 18,3 s | 6,0 h | 4.500 | **No** (faltan 2,1 s) |
| `rapido` | 12,2 s | 4,0 h | ~6.750 | No |
| `psicopata` | 9,15 s | 3,0 h | ~9.000 | No (suelo técnico ~12,6 s) |

**Cómo funciona el perfil**: es un **techo con relleno**. El motor mide lo que
tardó y, si va más rápido que el techo, reparte la diferencia en cuatro pausas
naturales (antes del F10, tras la ficha, entre páginas y al cerrar) con jitter.
Si el motor ya es más lento que el techo, **no añade pausas** y lo reporta en
las notas del ledger (`rapido 20.4/12.2s`).

Consecuencia práctica: hoy `rapido` y `psicopata` se comportan igual (los dos
por encima de su techo), y el que se cumple de verdad es `sigiloso`.

### Cadencias de teclas

| Nombre | ms por tecla | Uso |
| --- | --- | --- |
| `rapido` | 35 | producción |
| `humano` | 110 | si se quiere parecer más humano en el tecleo |

Se puede combinar cualquier perfil con cualquier cadencia:
`--perfil=sigiloso --teclas=humano`.

---

## 4. Guía de mejoras

Ordenadas por impacto real, con esfuerzo.

| # | Mejora | Gana | Esfuerzo | Riesgo |
| --- | --- | --- | --- | --- |
| 1 | Medir el ajuste de `espera_estado` por diff (hecho, sin medir) | ~0,5 s/dir | bajo | bajo |
| 2 | Verificar el pegado leyendo 2 celdas | detecta el 100 % de los fallos de pegado | medio | medio |
| 3 | Id por hash de la dirección (no posicional) | elimina fichas cruzadas al editar el CSV | bajo | bajo |
| 4 | Detectar uso humano del remoto y pausar | evita pelearse con el operador | medio | bajo |
| 5 | Leer el `Suscript` por portapapeles en vez de OCR | precisión 100 % en la columna clave | medio | medio |
| 6 | Reintentar la página (no la dirección) tras un fallo de pegado | no repite 15 filas ya pegadas | bajo | bajo |
| 7 | Panel `ui.py` con el semáforo por etapa en vivo | operación sin mirar logs | medio | bajo |

**Descartadas a propósito**: verificación post-pegado por contenido completo
(caro), perfil psicopata real (imposible), evadir controles del empleador.

---

## 5. Críticas

### Al sistema

1. **El pegador es a ciegas.** Después de pegar solo se comprueba que la
   pantalla cambió (`diff`), no que las celdas tengan lo correcto. Un pegado
   desalineado se detectaría tarde.
2. **El id es posicional.** Si se edita una fila del CSV, `D05` apunta a otra
   dirección. Ya costó fichas cruzadas una vez; ahora se valida por dirección
   al reanudar y al recuperar fichas, pero el riesgo de raíz sigue.
3. **Depende de una licencia gratuita de AnyDesk** que corta cada pocos
   minutos. El sistema se recupera (reconecta + reloguea + reanuda), pero paga
   ~10 s por corte.
4. **El OCR es el punto más frágil.** La cabecera `Suscript` se pierde con
   `psm 6` en algunas capturas y hay un plan B con `psm 11`. Funciona, pero es
   un parche sobre un comportamiento no determinista de Tesseract.
5. **Los perfiles no se cumplen** salvo `sigiloso`. El nombre promete más de lo
   que el motor entrega hoy.
6. **Un solo hilo, una sola ventana.** No hay paralelismo posible: el recurso
   (el escritorio remoto) es único.

### A mi propio trabajo

1. **La modularización rompió el F10 y costó una corrida.** Al mover
   `verifica_texto` a `matriz_buscar.py` se quedaron atrás `VERBOSE` y
   `ocr_text`. Ningún test lo cazó porque **todos parcheaban esa función en vez
   de ejecutarla**. Corregido con `test_integridad_modulos.py`, que analiza los
   16 módulos con `ast` y ejecuta `verifica_texto` de verdad.
2. **`separar.py` casi sobrescribe las 121 direcciones.** El flag `--salida`
   con espacio se ignoraba en silencio y el destino era producción. Lo salvó
   que Excel tenía el archivo bloqueado. Corregido con destino por defecto
   fuera de producción, guard `--produccion` y test de seguridad.
3. **El supervisor arrastraba un bug nunca ejecutado** (T7 comparaba filas
   contra ids). Se descubrió al primer lanzamiento real.
4. **Lección**: ningún refactor se da por bueno sin una corrida en vivo de una
   dirección. Los tests con mocks dan falsa confianza cuando parchean justo lo
   que se acaba de mover.

### Reglas que me impuse

- Nada de comandos en primer plano mientras el agente corre: le roban el foco a
  AnyDesk y el guard de inyección corta la dirección (pasó y mató D12).
- Un cambio a la vez, con suite verde y, si toca el motor, prueba en vivo.
- Los datos de clientes (`direcciones.csv`, `ledger.csv`) no van a git.

---

## 6. Riesgos vivos

| Riesgo | Impacto | Mitigación actual |
| --- | --- | --- |
| Corte de licencia AnyDesk | pausa de ~10 s | reconexión + re-login automáticos |
| Excel abierto | fichas al respaldo | `merge_fichas_pendientes` con validación |
| Geometría del 5250 cambia | coordenadas malas | se recalculan por píxeles en cada bloque |
| Taskbar reordenada | icono no encontrado | búsqueda por plantilla, no por posición |
| Pantalla usada por una persona | el agente escribe encima | sin detección (mejora #4 pendiente) |
| Ids posicionales | fichas cruzadas | validación por dirección (parcial) |
| Hoja cambiada de pestaña | pega en otro sitio | contrato de columnas (parcial) |
