import win32gui


def compute_target_points(source_anchor, current_pos, targets):
    if not source_anchor or not current_pos:
        return []
    sx, sy = source_anchor
    cx, cy = current_pos
    dx = cx - sx
    dy = cy - sy

    points = []
    for t in targets:
        ax, ay = t["anchor"]
        tx = ax + dx
        ty = ay + dy

        # Clamp to client rect
        try:
            left, top, right, bottom = _client_rect_screen(t["hwnd"])
            tx = max(left, min(tx, right - 1))
            ty = max(top, min(ty, bottom - 1))
        except Exception:
            pass

        points.append({"hwnd": t["hwnd"], "pos": (tx, ty)})

    return points


def _client_rect_screen(hwnd):
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    # Convert client top-left to screen
    pt = win32gui.ClientToScreen(hwnd, (0, 0))
    return (pt[0], pt[1], pt[0] + (right - left), pt[1] + (bottom - top))
