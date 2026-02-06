# -*- coding: utf-8 -*-
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from input_hook import InputListener
from target_manager import list_vmware_windows, resolve_hwnd_by_title
from mapping import compute_target_points
from replicator import MouseReplicator, KeyboardReplicator

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(os.path.dirname(APP_DIR), "config.json")


def format_anchor(anchor):
    if not anchor:
        return "-"
    return f"({anchor[0]}, {anchor[1]})"


class AppState:
    def __init__(self):
        self.source_anchor = None
        self.targets = []  # list of dicts: {hwnd, title, anchor, enabled}
        self.sync_on = False


class AppUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VMware Multi Cursor Sync (MVP)")
        self.state = AppState()

        self.mouse_rep = MouseReplicator()
        self.key_rep = KeyboardReplicator()

        self.listener = InputListener(
            on_mouse=self.on_mouse_event,
            on_key=self.on_key_event,
            on_hotkey=self.on_hotkey,
        )
        self.listener.start()

        self.build_ui()
        self.refresh_windows()

    def build_ui(self):
        self.root.geometry("900x520")

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Windows list
        ttk.Label(left, text="VMware Windows").pack(anchor=tk.W)
        self.win_list = tk.Listbox(left, height=12)
        self.win_list.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(left)
        btns.pack(fill=tk.X, pady=6)
        ttk.Button(btns, text="Refresh", command=self.refresh_windows).pack(side=tk.LEFT)
        ttk.Button(btns, text="Add to targets", command=self.add_target).pack(side=tk.LEFT, padx=6)

        # Targets
        ttk.Label(right, text="Targets").pack(anchor=tk.W)
        columns = ("enabled", "title", "anchor")
        self.targets_view = ttk.Treeview(right, columns=columns, show="headings", height=12)
        self.targets_view.heading("enabled", text="Enabled")
        self.targets_view.heading("title", text="Window")
        self.targets_view.heading("anchor", text="Anchor")
        self.targets_view.column("enabled", width=50, anchor=tk.CENTER)
        self.targets_view.column("title", width=360)
        self.targets_view.column("anchor", width=120, anchor=tk.CENTER)
        self.targets_view.pack(fill=tk.BOTH, expand=True)

        tbtns = ttk.Frame(right)
        tbtns.pack(fill=tk.X, pady=6)
        ttk.Button(tbtns, text="Toggle target", command=self.toggle_target).pack(side=tk.LEFT)
        ttk.Button(tbtns, text="Set target anchor", command=self.set_anchor_target).pack(side=tk.LEFT, padx=6)

        # Controls
        ctl = ttk.Frame(main)
        ctl.pack(fill=tk.X, pady=10)

        ttk.Button(ctl, text="Set source anchor", command=self.set_source_anchor).pack(side=tk.LEFT)
        ttk.Button(ctl, text="Save layout", command=self.save_layout).pack(side=tk.LEFT, padx=6)
        ttk.Button(ctl, text="Load layout", command=self.load_layout).pack(side=tk.LEFT)

        self.sync_btn = ttk.Button(ctl, text="Enable Sync", command=self.toggle_sync)
        self.sync_btn.pack(side=tk.RIGHT)

        self.status = ttk.Label(ctl, text="Sync: OFF", foreground="#b00020")
        self.status.pack(side=tk.RIGHT, padx=10)

        info = ttk.Label(
            self.root,
            text="Hotkeys: Ctrl+Alt+S (Toggle sync), Ctrl+Alt+Esc (Kill), Alt+1/2/3... (Toggle target)"
        )
        info.pack(fill=tk.X, padx=10, pady=(0, 6))

    def refresh_windows(self):
        self.win_list.delete(0, tk.END)
        self._windows = list_vmware_windows()
        for w in self._windows:
            self.win_list.insert(tk.END, f"{w['title']} (hwnd={w['hwnd']})")

    def add_target(self):
        sel = self.win_list.curselection()
        if not sel:
            messagebox.showinfo("Notice", "Select a VMware window first.")
            return
        idx = sel[0]
        w = self._windows[idx]
        target = {
            "hwnd": w["hwnd"],
            "title": w["title"],
            "anchor": None,
            "enabled": True,
        }
        self.state.targets.append(target)
        self.refresh_targets()

    def refresh_targets(self):
        for item in self.targets_view.get_children():
            self.targets_view.delete(item)
        for i, t in enumerate(self.state.targets, start=1):
            self.targets_view.insert(
                "",
                tk.END,
                iid=str(i - 1),
                values=("ON" if t["enabled"] else "OFF", t["title"], format_anchor(t["anchor"]))
            )

    def toggle_target(self):
        sel = self.targets_view.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.state.targets[idx]["enabled"] = not self.state.targets[idx]["enabled"]
        self.refresh_targets()

    def set_source_anchor(self):
        # Set to current cursor position
        pos = self.mouse_rep.get_cursor_pos()
        self.state.source_anchor = pos
        messagebox.showinfo("Source anchor", f"Source anchor set: {format_anchor(pos)}")

    def set_anchor_target(self):
        sel = self.targets_view.selection()
        if not sel:
            messagebox.showinfo("Notice", "Select a target first.")
            return
        idx = int(sel[0])
        messagebox.showinfo("Set Anchor", "Click OK, then click the desired position inside the VM window.")
        # Capture next left click position
        pos = self.listener.capture_next_click()
        if not pos:
            messagebox.showwarning("Set Anchor", "No click captured.")
            return
        self.state.targets[idx]["anchor"] = pos
        self.refresh_targets()

    def toggle_sync(self):
        self.state.sync_on = not self.state.sync_on
        self.update_sync_state()

    def update_sync_state(self):
        if self.state.sync_on:
            self.status.config(text="Sync: ON", foreground="#0a7f2e")
            self.sync_btn.config(text="Disable Sync")
            # Auto set source anchor if not set
            if not self.state.source_anchor:
                self.state.source_anchor = self.mouse_rep.get_cursor_pos()
        else:
            self.status.config(text="Sync: OFF", foreground="#b00020")
            self.sync_btn.config(text="Enable Sync")

    def kill_sync(self):
        self.state.sync_on = False
        self.update_sync_state()

    def on_hotkey(self, name):
        if name == "toggle_sync":
            self.toggle_sync()
        elif name == "kill":
            self.kill_sync()
        elif name.startswith("toggle_target_"):
            idx = int(name.split("_")[-1])
            if 0 <= idx < len(self.state.targets):
                self.state.targets[idx]["enabled"] = not self.state.targets[idx]["enabled"]
                self.refresh_targets()

    def on_mouse_event(self, event_type, data):
        if not self.state.sync_on:
            return
        if not self.state.source_anchor:
            return

        targets = [t for t in self.state.targets if t["enabled"] and t["anchor"]]
        if not targets:
            return

        points = compute_target_points(self.state.source_anchor, data.get("pos"), targets)
        self.mouse_rep.replicate(event_type, data, points)

    def on_key_event(self, event_type, data):
        if not self.state.sync_on:
            return
        targets = [t for t in self.state.targets if t["enabled"]]
        if not targets:
            return
        self.key_rep.replicate(event_type, data, targets)

    def save_layout(self):
        payload = {
            "source_anchor": self.state.source_anchor,
            "targets": self.state.targets,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Save layout", "Layout saved.")

    def load_layout(self):
        if not os.path.exists(CONFIG_PATH):
            messagebox.showwarning("Load layout", "No config file found.")
            return
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.state.source_anchor = payload.get("source_anchor")
        self.state.targets = payload.get("targets", [])

        # Resolve hwnd by title in case changed
        for t in self.state.targets:
            if not self.mouse_rep.is_window_valid(t.get("hwnd")):
                new_hwnd = resolve_hwnd_by_title(t.get("title", ""))
                if new_hwnd:
                    t["hwnd"] = new_hwnd

        self.refresh_targets()
        messagebox.showinfo("Load layout", "Layout loaded.")


if __name__ == "__main__":
    root = tk.Tk()
    app = AppUI(root)
    root.mainloop()

