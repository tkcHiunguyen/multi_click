import threading
from pynput import mouse, keyboard


class InputListener:
    def __init__(self, on_mouse, on_key, on_hotkey):
        self.on_mouse = on_mouse
        self.on_key = on_key
        self.on_hotkey = on_hotkey
        self._mouse_listener = None
        self._key_listener = None
        self._capture_next_click = False
        self._captured_pos = None
        self._pressed = set()

    def start(self):
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._key_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener.start()
        self._key_listener.start()

    def capture_next_click(self):
        self._capture_next_click = True
        self._captured_pos = None
        # Wait until click captured (simple blocking)
        for _ in range(200):
            if self._captured_pos:
                break
            threading.Event().wait(0.05)
        self._capture_next_click = False
        return self._captured_pos

    def _on_move(self, x, y):
        self.on_mouse("move", {"pos": (x, y)})

    def _on_click(self, x, y, button, pressed):
        if self._capture_next_click and pressed and button == mouse.Button.left:
            self._captured_pos = (x, y)
            return
        self.on_mouse(
            "click",
            {
                "pos": (x, y),
                "button": button.name,
                "pressed": pressed,
            },
        )

    def _on_scroll(self, x, y, dx, dy):
        self.on_mouse("scroll", {"pos": (x, y), "dx": dx, "dy": dy})

    def _on_key_press(self, key):
        self._pressed.add(key)
        self._check_hotkeys(key, True)
        self.on_key("down", {"key": key})

    def _on_key_release(self, key):
        if key in self._pressed:
            self._pressed.remove(key)
        self.on_key("up", {"key": key})

    def _check_hotkeys(self, key, pressed):
        # Ctrl+Alt+S toggle sync
        if self._is_combo({keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode.from_char('s')}, key):
            self.on_hotkey("toggle_sync")
            return
        # Ctrl+Alt+Esc kill
        if self._is_combo({keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.esc}, key):
            self.on_hotkey("kill")
            return
        # Alt+1..9 toggle target index
        for i in range(1, 10):
            if self._is_combo({keyboard.Key.alt_l, keyboard.KeyCode.from_char(str(i))}, key):
                self.on_hotkey(f"toggle_target_{i-1}")
                return

    def _is_combo(self, combo, last_key):
        # check if last_key is part of combo and all combo keys are pressed
        if last_key not in combo:
            return False
        return all(k in self._pressed or k == last_key for k in combo)
