"""Read-only: list child windows of an AnyDesk window with client rects.

The AnyDesk control window includes its own toolbar, so clicking a point in
the root client area does NOT land on the corresponding remote pixel.
The remote screen is a child window; this finds it.

Usage: python tools/children.py [hwnd]
"""
import ctypes
import sys
from ctypes import wintypes

from _mcp import need_hwnd

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
)


def describe(hwnd: int, root: int, depth: int) -> str:
    """Return one indented line with class, title and client geometry."""
    cls = ctypes.create_unicode_buffer(256)
    title = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    user32.GetWindowTextW(hwnd, title, 256)

    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))

    pad = "  " * depth
    return (
        f"{pad}{hwnd} class={cls.value!r} title={title.value!r} "
        f"client={rect.right - rect.left}x{rect.bottom - rect.top} "
        f"at=({origin.x - root[0]},{origin.y - root[1]})"
    )


def walk(hwnd: int, root: tuple[int, int], depth: int = 0, max_depth: int = 3):
    """Print the child tree below hwnd."""
    if depth > max_depth:
        return
    found: list[int] = []

    def callback(child, _lparam):
        found.append(child)
        return True

    user32.EnumChildWindows(hwnd, WNDENUMPROC(callback), 0)
    if not found:
        return
    # EnumChildWindows is recursive; show only direct children per level.
    direct = []
    for child in found:
        if user32.GetParent(child) == hwnd:
            direct.append(child)
    for child in direct:
        print(describe(child, root, depth))
        walk(child, root, depth + 1, max_depth)


if __name__ == "__main__":
    hwnd = need_hwnd(sys.argv)
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    root = (origin.x, origin.y)
    print(f"ROOT {describe(hwnd, root, 0)}")
    walk(hwnd, root)
