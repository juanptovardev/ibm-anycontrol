# ADR-0003 — Clics relativos al viewport + override del clic de centro

- **Fecha**: 2026-10-27
- **Estado**: Aceptada
- **Ámbito**: `dev/mcp-anydesk` (v3.7.0) + `dev/matriz-ibm-agent`

## Contexto
El fallo que rompió el ciclo manual durante muchas rondas: cada escritura
mandaba el texto al campo equivocado (Nombre en vez de Calle). La causa real no
era "el operador no puso el cursor": `window_manager.focus_and_verify()` hacía
`_click_window_center(hwnd)` en **cada** foco, porque `FOCUS_CLICK_ENABLED=True`
en la config. Es decir, cada escritura primero movía el cursor remoto al centro
de la ventana y escribía allí. El emulador respondía "El campo requiere
caracteres numericos" / "área protegida".

Además, la ventana de AnyDesk **no es** la pantalla remota: su área de cliente
incluye la barra de AnyDesk (~104 px). La pantalla remota es un hijo
(`gui.tabbar_panel`) con su propio offset.

## Decisión
1. `set_focus_click_mode(enabled)` introduce un override **por sesión** que
   desactiva el clic de centro; los flujos GUI lo desactivan explícitamente.
2. `find_viewport(root_hwnd)` resuelve el hijo que es la pantalla remota y
   devuelve su offset en coordenadas de cliente de la raíz.
3. `click_point(x, y)` usa coordenadas **relativas al viewport** y reporta
   `mapped_via: viewport|window`.
4. Las coordenadas nunca se cachean: `tools/rows.py` re-mide las filas por
   píxeles en cada ejecución (el operador redimensiona la ventana).

## Consecuencias
- Positivo: el foco ya no "contamina" la posición del cursor remoto.
- Positivo: el mapeo local es exacto y verificable (`GetCursorPos` == punto
  pedido).
- Negativo: cada sesión MCP debe resolver el hwnd del viewport: el hwnd **cambia
  por sesión** (393712→3146792→5702798→6162232→1966118→67230). Nunca cachear.
- Negativo: dos tools extra en el server (`geometry`, `click_point`) y una
  dependencia de `mss`/PIL para el fallback de captura.
