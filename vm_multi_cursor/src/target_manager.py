import win32gui
import win32process


def list_vmware_windows():
    windows = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        # Quick filter by title
        if "VMware" not in title:
            return
        windows.append({"hwnd": hwnd, "title": title})

    win32gui.EnumWindows(enum_handler, None)
    return windows


def resolve_hwnd_by_title(title):
    if not title:
        return None
    result = None

    def enum_handler(hwnd, _):
        nonlocal result
        if result:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = win32gui.GetWindowText(hwnd)
        if t == title:
            result = hwnd

    win32gui.EnumWindows(enum_handler, None)
    return result
