# DOSSIER DE CIERRE — IBM ANYCONTROL

> **Instrucciones:** completar cada sección con evidencia real. No borrar los títulos. Si un campo no aplica, escribir `N/A` y el motivo. Al final, el revisor ciego firma. Un dossier sin output pegado no es válido.

---

## 1. Identificación

| Campo | Valor |
|---|---|
| Proyecto | IBM AnyControl (`ibm-anycontrol`) |
| Versión / release | ______________________ |
| Fecha de cierre | ______________________ |
| Encargado de Finiquito | ______________________ |
| Revisor ciego | ______________________ |
| Operador | ______________________ |
| Baseline (ZIP + hash) | ______________________ |
| Snapshot / commit final | ______________________ |
| Entorno | Windows ____ / Python ____ / AnyDesk ____ / mcp-anydesk ____ |

---

## 2. Alcance del finiquito

### 2.1 Incluido

- Cierre de P0/S1: ______________________
- Cierre de P1: ______________________
- Correcciones documentales: ______________________
- Release candidate: ______________________

### 2.2 Excluido

- Features nuevas: ______________________
- Cambios de alcance funcional: ______________________
- Migraciones de datos no autorizadas: ______________________
- Waivers: ______________________

### 2.3 Decisiones del operador

| ID | Decisión | Resultado | Fecha |
|---|---|---|---|
| D-01 | Jev on/off | | |
| D-02 | Versionar datos | | |
| D-03 | Panel LAN/localhost | | |
| D-04 | Git local/snapshots | | |
| D-05 | Ventana de corrida | | |
| D-06 | Revisor ciego | | |
| D-07 | Waivers | | |

---

## 3. Baseline y restore

| Ítem | Resultado | Evidencia |
|---|---|---|
| ZIP creado | | `evidencia/WP-00/backup.txt` |
| Manifiesto >=128 filas | | `manifest.csv` |
| Restore en temp | | `restore.txt` |
| Hashes original = restore | | `hashes.txt` |
| `direcciones.csv` 2168 filas | | |
| `ledger.csv` 52 filas | | |
| `direcciones_segunda.csv` 2167 filas | | |
| Autorización del operador | | |

**Hash de archivos críticos (antes):**

```text
direcciones.csv: ______________________
ledger.csv: ______________________
direcciones_segunda.csv: ______________________
datos.csv: ______________________
```

---

## 4. Cambios por work package

| WP | Objetivo | Archivos tocados | Snapshot/commit | Estado | Evidencia |
|---|---|---|---|---|---|
| WP-00 | Baseline | | | | |
| WP-01 | Preflight | | | | |
| WP-02 | PII/Jev | | | | |
| WP-03 | CSV atómico | | | | |
| WP-04 | Hoja fail-closed | | | | |
| WP-05 | Panel | | | | |
| WP-06 | Higiene | | | | |
| WP-07 | Contrato único | | | | |
| WP-08 | Id estable | | | | |
| WP-09 | Reconciliación | | | | |
| WP-10 | Lock | | | | |
| WP-11 | Runner/tests | | | | |
| WP-12 | Kill acotado | | | | |
| WP-13 | Docs/ADRs | | | | |

**Resumen de diff:** ______________________

---

## 5. Evidencia de aceptación

> Pegar el comando y el output real, no un resumen. Un bloque por WP.

### WP-01

```text
Comando:
Output:
Exit code:
```

### WP-02

```text
Comando:
Output:
Exit code:
```

### WP-03

```text
Comando:
Output:
Exit code:
```

### WP-04

```text
Comando:
Output:
Exit code:
```

### WP-05

```text
Comando:
Output:
Exit code:
```

### WP-06

```text
Comando:
Output:
Exit code:
```

### WP-07..WP-13

```text
Comando:
Output:
Exit code:
```

---

## 6. Tests

| Métrica | Antes | Después |
|---|---|---|
| Total | | |
| Passed | | |
| Failed | | |
| Skipped | | |
| Duración | | |
| Runner | | |
| Artefacto | | `tools/verifications/verify-*.json` |

**Conteo oficial:** ______________________ (desde `test_count.txt`)

**Tests que requieren GUI/Excel (skip justificado):**

| Test | Motivo | Cómo se validó manualmente |
|---|---|---|
| | | |

**Regresión:** `[ ]` sin regresiones · `[ ]` con regresiones (detallar)

---

## 7. Seguridad y PII

| Control | Estado | Evidencia |
|---|---|---|
| Jev off por defecto o clave dedicada | | |
| Sin credencial personal de OpenCode | | |
| `PRIVACY.md` publicado | | |
| Sin secretos en el árbol | | |
| `.gitignore` actualizado | | |
| `ui_token.txt` con ACL | | |
| Panel en localhost por defecto | | |
| Token >=22 y header-only | | |
| Rate limit activo | | |
| `/api/matar` con confirmación | | |
| Datos versionados: sí/no | | |

**Incidentes PII durante el finiquito:** `[ ]` ninguno · `[ ]` detallar

---

## 8. Integridad de datos

| Control | Resultado |
|---|---|
| `direcciones.csv` 2168 filas | |
| 206 fichas preservadas | |
| Sin duplicados nuevos | |
| `.bak` generado | |
| Test de fallo inyectado | |
| Restore probado | |
| Ledger sin duplicados por id | |
| Evidencia con rutas relativas | |

**Hash final:**

```text
direcciones.csv: ______________________
ledger.csv: ______________________
```

---

## 9. Riesgos y reservas

| ID | Riesgo | Estado | Mitigación | Responsable |
|---|---|---|---|---|
| | | | | |

**Waivers firmados:**

| Riesgo | Motivo | Vigencia | Aprobado por |
|---|---|---|---|
| | | | |

**Riesgos S1 abiertos:** `[ ]` 0 · `[ ]` hay (el release se rechaza)

---

## 10. Rollback

| Paso | Comando | Resultado esperado |
|---|---|---|
| 1 | Restaurar ZIP del baseline | Archivos originales |
| 2 | Comparar hashes | Iguales a WP-00 |
| 3 | Restaurar `direcciones.csv` y `ledger.csv` | Conteos 2168/52 |
| 4 | Detener procesos | Sin python del proyecto |
| 5 | Rotar token/credenciales si hubo incidente | Token nuevo |

**Tiempo estimado de rollback:** ______________________
**Responsable:** ______________________

---

## 11. Veredicto

- `[ ]` **CERRADO** — DoD completo; sin reservas.
- `[ ]` **CERRADO CON RESERVAS** — P1/P2 con waiver firmado; sin S1.
- `[ ]` **RECHAZADO** — falta un P0, hay S1, o la evidencia no es re-ejecutable.

**Justificación:**

____________________________________________________________________________

____________________________________________________________________________

---

## 12. Firmas

| Rol | Nombre | Fecha | Firma |
|---|---|---|---|
| Encargado de Finiquito | | | |
| Revisor ciego | | | |
| Operador | | | |

**Anexos:**

- [ ] `CHECKLIST_FINIQUITO.md` completo
- [ ] `evidencia/WP-00/` a `evidencia/WP-13/`
- [ ] `tools/verifications/verify-*.json`
- [ ] ADR-0007 y ADR-0008
- [ ] `README_OPERACION.md`
- [ ] ZIP + SHA256 del release
