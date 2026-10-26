"""Native 1:1 capture of a window's client area. Read-only, no input.

The MCP screenshot tool caps width at 640px, which breaks coordinate mapping
(1024 -> 640 is a 1.6 factor). This grabs the client area pixel-for-pixel so
pixel coordinates match click_point() coordinates exactly.

Primary path is PrintWindow(PW_RENDERFULLCONTENT), which works even when the
AnyDesk window is occluded. Falls back to a screen grab (mss) if the result
comes back blank.

Usage: python tools/native_shot.py [hwnd] [label]
"""
import ctypes
import sys
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import mss
from PIL import Image

from _mcp import need_hwnd

OUT = Path(__file__).resolve().parent.parent / "evidencia"
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def client_box(hwnd: int) -> tuple[int, int, int, int]:
    """Return (left, top, width, height) of the client area in screen pixels."""
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise SystemExit(f"GetClientRect failed for {hwnd}")
    origin = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise SystemExit(f"ClientToScreen failed for {hwnd}")
    return origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top


def print_window(hwnd: int, w: int, h: int) -> Image.Image:
    """Capture the window surface even when occluded (PrintWindow)."""
    hdc = user32.GetWindowDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    old = gdi32.SelectObject(memdc, bmp)
    try:
        if not user32.PrintWindow(hwnd, memdc, PW_RENDERFULLCONTENT):
            raise RuntimeError("PrintWindow returned 0")

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # top-down rows
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0  # BI_RGB

        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bmi), 0):
            raise RuntimeError("GetDIBits failed")
        return Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1)
    finally:
        gdi32.SelectObject(memdc, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(hwnd, hdc)


def screen_grab(hwnd: int) -> Image.Image:
    """Capture the client area from the screen (requires the window visible)."""
    x, y, w, h = client_box(hwnd)
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
    return Image.frombytes("RGB", shot.size, shot.rgb)


def grab(hwnd: int, allow_screen_fallback: bool = True) -> Image.Image:
    """Capture the client area at 1:1, preferring the occluded-safe path."""
    _, _, w, h = client_box(hwnd)
    try:
        img = print_window(hwnd, w, h)
        if img.convert("L").getextrema() != (0, 0):
            return img
    except Exception:
        pass
    if not allow_screen_fallback:
        raise SystemExit("PrintWindow failed and screen fallback disabled")
    return screen_grab(hwnd)


def save(img: Image.Image, label: str = "") -> Path:
    """Save a capture into evidencia/ and return the path."""
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"-{label}" if label else ""
    path = OUT / f"native-{stamp}{tag}.png"
    img.save(path)
    return path


if __name__ == "__main__":
    hwnd = need_hwnd(sys.argv)
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    image = grab(hwnd)
    path = save(image, label)
    print(f"client={client_box(hwnd)} size={image.size} path={path}")
