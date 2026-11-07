"""Un disparo: palabras OCR de la zona del listado (depuracion de A1)."""
import sys

import pytesseract

sys.path.insert(0, "tools")
import native_shot  # noqa: E402

sys.path.insert(0, r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk")
from mcp_anydesk_server import window_manager as W  # noqa: E402

hwnd = int(sys.argv[1])
vp = W.find_viewport(hwnd)
img = native_shot.grab(vp["hwnd"])
print("viewport", vp["hwnd"], img.size)
d = pytesseract.image_to_data(img, config="--psm 6", output_type=pytesseract.Output.DICT)
for i, t in enumerate(d["text"]):
    t = (t or "").strip()
    if not t:
        continue
    print(f"{d['top'][i]:4d} {d['left'][i]:4d} {d['width'][i]:4d} {d['height'][i]:3d} {t!r}")
