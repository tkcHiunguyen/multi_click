import ctypes
import win32gui
import win32api
import win32con


class MouseReplicator:
    def __init__(self):
        pass

    def get_cursor_pos(self):
        return win32api.GetCursorPos()

    def is_window_valid(self, hwnd):
        return bool(hwnd) and win32gui.IsWindow(hwnd)

    def replicate(self, event_type, data, points):
        for p in points:
            hwnd = p["hwnd"]
            x, y = p["pos"]
            try:
                client = win32gui.ScreenToClient(hwnd, (x, y))
            except Exception:
                continue
            lparam = (client[1] << 16) | (client[0] & 0xFFFF)

            if event_type == "move":
                win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
            elif event_type == "click":
                btn = data.get("button", "left")
                pressed = data.get("pressed", False)
                if btn == "left":
                    msg = win32con.WM_LBUTTONDOWN if pressed else win32con.WM_LBUTTONUP
                    wparam = win32con.MK_LBUTTON if pressed else 0
                elif btn == "right":
                    msg = win32con.WM_RBUTTONDOWN if pressed else win32con.WM_RBUTTONUP
                    wparam = win32con.MK_RBUTTON if pressed else 0
                else:
                    msg = win32con.WM_MBUTTONDOWN if pressed else win32con.WM_MBUTTONUP
                    wparam = win32con.MK_MBUTTON if pressed else 0
                win32api.PostMessage(hwnd, msg, wparam, lparam)
            elif event_type == "scroll":
                dy = data.get("dy", 0)
                # wheel delta in high word
                wparam = (dy * 120) << 16
                win32api.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)


class KeyboardReplicator:
    def __init__(self):
        pass

    def replicate(self, event_type, data, targets):
        key = data.get("key")
        vk = self._to_vk(key)
        if vk is None:
            return
        msg = win32con.WM_KEYDOWN if event_type == "down" else win32con.WM_KEYUP
        for t in targets:
            hwnd = t["hwnd"]
            win32api.PostMessage(hwnd, msg, vk, 0)

    def _to_vk(self, key):
        # pynput Key or KeyCode
        if hasattr(key, "vk") and key.vk is not None:
            return key.vk
        try:
            ch = key.char
            return ord(ch.upper()) if ch else None
        except Exception:
            return None
