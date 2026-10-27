"""Valida el mapa de teclas sin enviar ni un evento (solo ctypes de lectura).

f13..f24 no se incluyen: no son VKs alcanzables por teclado; el emulador 5250
recibe F13..F24 como shift+f1..f12, que es justo como se usa aqui (shift+f4).
"""
import sys

sys.path.insert(0, r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk")
from mcp_anydesk_server import keyboard_injector as k  # noqa: E402

FLUJO = ["down", "right", "shift", "ctrl", "alt", "add", "f4", "f10", "f12",
         "escape", "home", "delete", "tab", "pageup", "pagedown", "insert",
         "up", "left", "end", "space", "backspace"]

faltan = [n for n in FLUJO if n not in k._VK_CODES]
print("mapa_teclas:", len(k._VK_CODES), "| faltan:", faltan or "NINGUNA")

for n in ["down", "right", "shift", "add", "f10", "f4", "tab", "delete"]:
    vk = k._VK_CODES[n]
    scan = k.MapVirtualKeyW(vk, 0)
    print(f"  {n:7s} vk=0x{vk:02X} scan={scan:3d} ext={vk in k._EXTENDED_VK}")

letras = [c for c in "abcdefghijklmnopqrstuvwxyz" if c in k._VK_CODES]
print("letras_en_mapa:", letras or "NINGUNA (press_keys no teclea texto)")

mods = {m: k._VK_CODES.get(m) for m in ("shift", "ctrl", "alt")}
print("modificadores:", {m: hex(v) if v else None for m, v in mods.items()})

print("paste_shift_param:", "shift" in k.paste_clipboard.__code__.co_varnames)
sys.exit(0 if not faltan else 1)
