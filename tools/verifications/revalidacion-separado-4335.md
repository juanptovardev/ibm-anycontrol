# Revalidación — separación de las 4335 direcciones

## Causa raíz
`datos/direcciones.csv` tenía **4335 direcciones ENTERAS en una sola columna** (`parte1`), con `parte2` vacío. Nunca se corrió `separar.py` sobre el lote. El agente escribía la dirección completa en "Calle" y "No.Casa" quedaba vacío → el F10 no encontraba nada (las 13 primeras salieron `no_encontrado`).

## Fix aplicado (sin lanzar el agente)
Separé las 4335 con `separar.parse`:

| Resultado  | Cantidad | %     |
| ---------- | -------- | ----- |
| Separadas  | 4282     | 98,8% |
| Con problema | 53     | 1,2%  |

- Backup del original: `datos/direcciones_backup_previosplit_20261107-110340.csv`
- Lista de las 53 (una por línea): `datos/direcciones_problema.txt`
- Verificado: el CSV nuevo tiene 4282 filas con `parte2` relleno (`CR 12B` / `140-55`), 53 con `parte2` vacío (se conservaron tal cual).

## Las 53 con problema (malformadas en la fuente, no es el código)
1. **Formato "KR" / intersección** (ej. `KR 22 A CL 10 S 44`, `KR 20 CL 20 A 85`, `TV 12 A CL 5 E 18`) — parecen doble calle o un sistema distinto. ~20 casos.
2. **"BIS" + letra + "SUR" mal pegados** (ej. `CR 89BISASUR 59C-15`, `TV 72NBISASUR 40-40`, `CR 107BISB 71A-6`) — la fuente tiene la letra del bis/Sur garbleada. ~30 casos.
3. Sueltos (`CL 80 BIS S 91 90`).

Las 53 quedan como `parte1=dirección entera, parte2=vacío` → en la corrida saldrán `no_encontrado` (no rompen nada) y quedan listadas para revisar a mano.

## Acción siguiente (cuando me des GO)
Relanzar `supervisor.py --perfil=psicopata --teclas=rapido --max-vueltas=20 --horas=30 --tope-vuelta=21600` sobre las 4335. Las 53 raras saldrán "no encontrada".

## Pregunta para ti
¿Las 53 las dejo como "no encontrada" (recomendado, las revisamos después a mano), o querés que intente partirlas yo (riesgo de partirlas mal en Calle/No.Casa)?