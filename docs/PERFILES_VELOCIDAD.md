# Perfiles de velocidad y optimizaciones del motor

## Los 4 perfiles (definidos por el operador el 03/11/2026)

El ritmo de referencia es el del operador: **18,3 s por direccion** (4.500
leads en 6 h, unas 20.000 lineas pegadas, ~1.180 direcciones).

| #   | Perfil    | Factor            | Techo s/dir | Dia completo (1.180 dir) | En 6 h       |
| --- | --------- | ----------------- | ----------- | ------------------------ | ------------ |
| 1   | Sigiloso  | 1,5x mas lento    | **27,5**    | **9,0 h**                | ~3.000 leads |
| 2   | Humano    | el del operador   | **18,3**    | **6,0 h**                | 4.500 leads  |
| 3   | Rapido    | 1,5x mas rapido   | **12,2**    | **4,0 h**                | ~6.750 leads |
| 4   | Psicopata | 2x mas rapido     | **9,15**    | **3,0 h**                | ~9.000 leads |

**Techo, no objetivo a alcanzar.** El motor NO acelera por debajo del techo:
mide cuanto tardo de verdad y reparte el sobrante en cuatro pausas naturales
(con jitter), para que el ritmo no sea una maquina de pulsos. Si no llega al
techo, lo dice en las notas de la direccion: nunca se finge.

El perfil **psicopata es inalcanzable** con AnyDesk: el suelo medido esta en
~12,6 s por direccion (el Alt+Tab tarda 1-3 s en llegar al remoto y el
portapapeles remoto no se puede leer).

## Uso

```powershell
python tools\autonomo.py --perfil=sigiloso          # una pasada
python tools\supervisor.py --perfil=sigiloso        # el bucle de lote
python tools\supervisor.py --perfil=humano --teclas=humano
```

- `MATRIZ_PERFIL` / `--perfil=`: nombre del perfil (sigiloso | humano | rapido
  | psicopata). Por defecto `humano`.
- `MATRIZ_TECLAS` / `--teclas=`: cadencia de teclas, `rapido` (35 ms, el motor
  actual) o `humano` (110 ms). **No va atado al perfil**: con 120 ms el perfil
  sigiloso no podria cumplir su propio techo. Con `humano` el motor se pasa de
  todos los techos y el informe lo dice.

## Donde se va el tiempo (medido, 03/11)

Reparto de una pagina de 9 s antes de optimizar:

| Componente                    | ms    | %   |
| ----------------------------- | ----- | --- |
| Esperas fijas (sleep)         | 3.700 | 41% |
| OCR (pantalla completa)        | 2.500 | 28% |
| Teclas + latencia MCP/AnyDesk | 2.200 | 25% |
| Capturas + PNG                 | 370   | 4%  |
| sel_box (informativo)          | 180   | 2%  |

## Optimizaciones aplicadas (capa A, C y D)

- **A. Las esperas fijas se sustituyen por verificacion activa.** El pegado
  se ve a los ~150 ms: se captura y se compara cada 120 ms en vez de dormir
  0,6 s. El sondeo del destino tras el Alt+Tab baja de 0,6 s a 0,35 s.
  El AvPag comprueba que la pantalla **cambio** antes de copiar: si no, se
  espera (si no, se pega la pagina anterior: duplicado).
- **C. Capturas reusadas.** La captura "antes del pegado" es la del sondeo de
  destino; no se vuelve a capturar.
- **D. Teclas contiguas en una sola llamada.** `derecha + izquierda +
  Suprimir` van juntas (el MCP cobra ~150 ms por llamada): la busqueda pasa de
  15 llamadas a 9.
- El OCR del formulario antes del F10 (~1 s) solo se paga cuando la Calle
  esta vacia o con `MATRIZ_VERBOSE=1`.

## Lo que NO se toco (y por que)

- **El OCR de la pantalla completa del listado** (932 ms): es el que decide el
  estado de la pantalla (listado / ficha / fin de archivo). Recortarlo puede
  hacer que la ficha del edificio se confunda con el formulario y el flujo se
  rompa. Se deja hasta que se pueda validar en vivo.
- **El cambio de ventana**: era el mayor coste y el mayor riesgo con `Alt+Tab`
  (superado: desde el 03/11 se usa el icono de la taskbar). La alternativa (5250 y
  Chrome lado a lado con clic directo) bajaria el suelo a ~10,7 s/dir, pero
  requiere cambiar el escritorio remoto.
- **La verificacion post-pegado por contenido**: descartada por el operador
  (sobrecoste).
