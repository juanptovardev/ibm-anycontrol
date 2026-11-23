# Cruce de direcciones del resultado con fichas

Fecha: 2026-11-19. Estado: analisis solamente, nada ejecutado ni modificado.

## Entradas

Origen de direcciones
- `C:\Users\juanp_8h8f07l\Downloads\resultadopruebasagentibm.csv`
- 57.744 bytes, sin BOM, saltos CRLF, una sola columna sin cabecera.
- 3.989 lineas, 319 direcciones distintas.
- 0 lineas con `;`, comillas o tabulador; 0 caracteres no ASCII; longitud entre 10 y 17 caracteres.

Registro de fichas (fuente indicada por el operador)
- `C:\Users\juanp_8h8f07l\dev\matriz-ibm-agent-piloto100\datos\direcciones.csv`: 2.168 filas, 206 con ficha.
- `C:\Users\juanp_8h8f07l\dev\matriz-ibm-agent-piloto100\datos\direcciones_orden.csv`: 135 filas, 120 con ficha util. La ficha quedo escrita en la columna `estado` por un corrimiento de columnas del generador.
- Union depurada: 326 direcciones con ficha, 0 incompletas.

Formato de ficha
- Multilinea: `Cuenta: N` / `NOMBRE DEL EDIFICIO` / `DIRECCION INTERNA`.
- Un caso en una linea con separador `|`: `Cuenta: N | NOMBRE | DIRECCION`.
- El parser debe aceptar ambos formatos.

## Hallazgos

1. El archivo de resultado no es una lista de direcciones unicas: es una fila por suscriptor.
   - 336 bloques contiguos de direccion repetida.
   - Maximos: `CL 147 58C-00` 178 lineas, `CL 72F 113-48` 129, `CL 70 96-34` 84.
   - Implicacion: la salida debe conservar las 3.989 filas y el orden, sin deduplicar.

2. Cobertura por coincidencia exacta: 264 de 319 direcciones (2.787 de 3.989 lineas, 69,9%).

3. Cobertura ampliada usando la direccion interna de la ficha como alias: 314 de 319 direcciones (3.668 de 3.989 lineas, 92,0%).
   - Aporta 50 direcciones y 881 lineas.
   - Es inferencia, no verificacion: 54 de las 326 fichas tienen direccion interna distinta a la direccion buscada, y el alias mezcla porteria o prefijo.
   - Ejemplos del riesgo:
     - `CR 17A 136-76` recibiria la ficha de `CR 17A 136-66` (cuenta 21241, AGORA).
     - `AV 15 109-62` recibiria la ficha de `CR 15 109-62` (cuenta 10107, ARRAYANES).
     - `CR 54 128C-48` recibiria la ficha de `CR 58C 128B-18` (cuenta 16986, MIRADOR DE SOTILEZA III).

4. Sin ficha: 5 direcciones, 321 lineas (8,0%).
   - `CL 147 58C-00` 178 lineas: no aparece en ningun CSV del piloto.
   - `CL 72F 113-48` 129 lineas: no aparece en ningun CSV del piloto.
   - `CL 145A 13-70` 10 lineas: existe en `direcciones.csv` con ficha vacia.
   - `CL 95 20-12` 3 lineas: existe en `direcciones_orden.csv` y en backups de ledger, ficha vacia.
   - `CR 8 80-29` 1 linea: igual que la anterior.

5. Integridad del registro de fichas
   - 1 sola cuenta aparece en dos direcciones distintas.
   - Nombres de edificio entre 4 y 30 caracteres.
   - Todas las cuentas son numericas.
   - Las 206 fichas de `direcciones.csv` siguen el formato de tres lineas; ninguna incompleta.

## Propuesta de archivo de salida

Nombre: `resultadopruebasagentibm_fichas.csv` en `Downloads`. El original no se toca.

| Col | Contenido | Regla |
|---|---|---|
| A | Linea original | Copia byte a byte, mismo orden, 3.989 filas |
| B | Numero de cuenta matriz | De la ficha asociada |
| C | Nombre del edificio | Segunda linea de la ficha |
| D | Direccion de referencia inicial | `parte1 + " " + parte2` canonico de la fila del registro; si no hay match, la linea normalizada |
| E | Estado del cruce | `exacta`, `inferida`, `sin_ficha` |
| F | Fuente de la ficha | `direcciones.csv`, `direcciones_orden.csv` |

Formato tecnico: delimitador `;`, UTF-8 con BOM, CRLF, cabecera en la primera fila.

## Decisiones que necesitan luz verde

- D1. Usar solo coincidencia exacta (69,9% de las lineas) o incluir el alias por direccion interna (92,0%) marcado como `inferida`.
- D2. Incluir columnas E y F de trazabilidad, o dejar solo A-D.
- D3. Confirmar nombre y ruta del archivo de salida.
- D4. Que hacer con las 5 direcciones sin ficha: dejar B y C vacias, o extraerlas despues con el agente en una corrida corta (5 direcciones, no ejecutada ahora).

## Limites

- Los numeros salen de lectura de archivos, sin ejecutar el cruce ni escribir la salida.
- Una ficha corresponde a la cuenta que devolvio la busqueda por direccion en el 5250; no garantiza que la linea del suscriptor pertenezca a ese edificio.
- El alias por direccion interna debe tratarse como pista, nunca como dato verificado.

## Resultado de la ejecucion

Salida escrita: `C:\Users\juanp_8h8f07l\Downloads\resultadopruebasagentibm_fichas.csv`, 275.236 B.

| Metrica | Valor |
|---|---|
| Filas de datos | 3.989 (la original tiene 3.989 lineas) |
| `exacta` | 2.787 |
| `inferida` | 881 |
| `sin_ficha` | 321 |
| Alias ambiguos descartados | 1 |
| Filas con cuenta y nombre | 3.668 |

Verificado sobre la salida: BOM y 3.990 CRLF correctos, 6 columnas en todas las filas, columna A identica al original en las 3.989 filas, las 321 filas `sin_ficha` con B y C vacias y D igual a la linea normalizada, las 881 `inferida` con cuenta, direccion de referencia y fuente, y las 2.787 `exacta` con D igual a A.

Defecto encontrado y corregido durante la generacion: la rama `sin_ficha` asignaba una tupla `(None, None, None)`, que en Python es truthy, y escribia C y D vacias. Corregido a `None` antes de la corrida valida.

Las 5 direcciones sin ficha quedan con B y C vacias segun la decision D4. Si se quieren completar, requiere una corrida del agente sobre esas 5 direcciones contra el 5250.