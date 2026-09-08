# wc3_fishing_helper_fixed.py
# Automates UP/DOWN prompts in Twilight's Eve Evo RPG fishing using fast color masks.
# Fixes:
#  - Color inversion (auto-detects BGRA vs RGBA and corrects)
#  - Repeated same-direction prompts (robust rising-edge detection)
#
# Windows only. Run as Admin if WC3 runs as Admin.

import time, random, sys, json, threading
import numpy as np
import cv2
import keyboard
import pygetwindow as gw
from ctypes import windll

# ===================== Config =====================
WINDOW_TITLE_KEYWORD = "Warcraft"

# ROI persisted between runs (percent of game window)
CFG_FILE = "roi_config.json"
def load_cfg():
    try:
        with open(CFG_FILE, "r") as f: return json.load(f)
    except Exception: return {}
def save_cfg(d):
    with open(CFG_FILE, "w") as f: json.dump(d, f, indent=2)

_cfg = load_cfg()
ROI_X_MIN_PCT = _cfg.get("ROI_X_MIN_PCT", 0.35)
ROI_X_MAX_PCT = _cfg.get("ROI_X_MAX_PCT", 0.65)
ROI_Y_MIN_PCT = _cfg.get("ROI_Y_MIN_PCT", 0.75)
ROI_Y_MAX_PCT = _cfg.get("ROI_Y_MAX_PCT", 0.92)

# HSV thresholds for yellow (UP) and green (DOWN) — tweak if needed
# YELLOW_LOW  = np.array([20, 110, 110], dtype=np.uint8)
# YELLOW_HIGH = np.array([37, 255, 255], dtype=np.uint8)
YELLOW_LOW  = np.array([18, 100, 100])
YELLOW_HIGH = np.array([40, 255, 255])
GREEN_LOW   = np.array([45,  80, 110], dtype=np.uint8)
GREEN_HIGH  = np.array([85, 255, 255], dtype=np.uint8)

# Prompt detection thresholds
MIN_PIXELS     = 250   # >= this => prompt is "present"
CLEAR_PIXELS   = 120   # < this  => considered "cleared"
CLEAR_FRAMES   = 2     # need this many consecutive clear frames to reset prompt state

COOLDOWN_SEC        = 0.22                     # guard against accidental double-press
RANDOM_JITTER_SEC   = (0.010, 0.030)           # human-like variation

# Preview window (placed on monitor index below)
PREVIEW_MONITOR_INDEX = 1   # 0=primary, 1=second monitor, etc.
PREVIEW_W, PREVIEW_H = 1920, 1080
PREVIEW_WIN_NAME = "WC3 Fishing Preview"

# ===================== Screen capture =====================
class Capture:
    """Returns frames as *raw* numpy arrays from dxcam or mss.
       Color/order is auto-corrected later in detect() to avoid inversion issues."""
    def __init__(self):
        self.mode = None
        try:
            import dxcam
            self.dxcam = dxcam.create()
            _ = self.dxcam.grab()
            self.mode = "dxcam"
            self.mss = None
        except Exception:
            self.dxcam = None
            try:
                import mss
                self.mss = mss.mss()
                self.mode = "mss"
            except Exception as e:
                raise RuntimeError("No capture backend (dxcam/mss) available") from e

    def grab(self, region):
        l, t, r, b = region
        if self.mode == "dxcam":
            frame = self.dxcam.grab(region=(l, t, r, b))  # usually 4ch
            return frame
        else:
            monitor = {"left": l, "top": t, "width": r - l, "height": b - t}
            frame = np.array(self.mss.grab(monitor))      # BGRA
            return frame

# ===================== Window / ROI helpers =====================
def find_wc3_window(keyword):
    wins = gw.getWindowsWithTitle(keyword)
    if not wins:
        raise RuntimeError(f"Could not find a window with title containing '{keyword}'.")
    wins = [w for w in wins if w.width > 100 and w.height > 100]
    wins.sort(key=lambda w: w.width * w.height, reverse=True)
    win = wins[0]
    try:
        win.restore()
        win.activate()
    except Exception:
        pass
    return win

def roi_from_window(win):
    left, top, right, bottom = win.left, win.top, win.right, win.bottom
    w, h = right - left, bottom - top
    rx1 = left + int(w * ROI_X_MIN_PCT)
    rx2 = left + int(w * ROI_X_MAX_PCT)
    ry1 = top  + int(h * ROI_Y_MIN_PCT)
    ry2 = top  + int(h * ROI_Y_MAX_PCT)
    return (rx1, ry1, rx2, ry2)

def clamp01(x): return max(0.0, min(1.0, x))

def nudge_roi(win, move=None, resize=None):
    """Move (Alt+Arrows) or resize edges (Ctrl+Alt+Arrows) in 1% steps."""
    global ROI_X_MIN_PCT, ROI_X_MAX_PCT, ROI_Y_MIN_PCT, ROI_Y_MAX_PCT
    step = 0.01
    if move:
        dx, dy = move
        ROI_X_MIN_PCT = clamp01(ROI_X_MIN_PCT + dx*step)
        ROI_X_MAX_PCT = clamp01(ROI_X_MAX_PCT + dx*step)
        ROI_Y_MIN_PCT = clamp01(ROI_Y_MIN_PCT + dy*step)
        ROI_Y_MAX_PCT = clamp01(ROI_Y_MAX_PCT + dy*step)
    if resize:
        if resize == 'left':  ROI_X_MIN_PCT = clamp01(ROI_X_MIN_PCT - step)
        if resize == 'right': ROI_X_MAX_PCT = clamp01(ROI_X_MAX_PCT + step)
        if resize == 'up':    ROI_Y_MIN_PCT = clamp01(ROI_Y_MIN_PCT - step)
        if resize == 'down':  ROI_Y_MAX_PCT = clamp01(ROI_Y_MAX_PCT + step)
    region = roi_from_window(win)
    print(f"ROI %: x=({ROI_X_MIN_PCT:.3f},{ROI_X_MAX_PCT:.3f}) y=({ROI_Y_MIN_PCT:.3f},{ROI_Y_MAX_PCT:.3f}) -> {region}")
    return region

# ===================== Detection (with auto color-order fix) =====================
def _masks_from_bgr(frame_bgr):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask_y = cv2.inRange(hsv, YELLOW_LOW, YELLOW_HIGH)
    mask_g = cv2.inRange(hsv, GREEN_LOW, GREEN_HIGH)
    kernel = np.ones((3,3), np.uint8)
    mask_y = cv2.morphologyEx(mask_y, cv2.MORPH_OPEN, kernel, iterations=1)
    mask_g = cv2.morphologyEx(mask_g, cv2.MORPH_OPEN, kernel, iterations=1)
    y_count = int(np.count_nonzero(mask_y))
    g_count = int(np.count_nonzero(mask_g))
    return y_count, g_count, mask_y, mask_g

def detect_prompt_auto(frame_raw):
    """
    Accepts raw frame (possibly BGRA or RGBA). Returns:
    - decision: 'up' | 'down' | None
    - y_cnt, g_cnt
    - mask_y, mask_g
    - frame_bgr_used (for preview)
    Auto-selects the correct channel order to avoid color inversion.
    """
    if frame_raw is None:
        return None, 0, 0, None, None, None

    bgr_candidates = []
    if frame_raw.ndim == 3 and frame_raw.shape[2] == 4:
        # Try both interpretations and pick the one that yields stronger colored text
        try:
            bgr_a = cv2.cvtColor(frame_raw, cv2.COLOR_BGRA2BGR)
            bgr_candidates.append(("bgra", bgr_a))
        except Exception:
            pass
        try:
            bgr_b = cv2.cvtColor(frame_raw, cv2.COLOR_RGBA2BGR)
            bgr_candidates.append(("rgba", bgr_b))
        except Exception:
            pass
        if not bgr_candidates:
            # Fallback: drop alpha blindly
            frame_bgr = frame_raw[:, :, :3].copy()
            y_cnt, g_cnt, mask_y, mask_g = _masks_from_bgr(frame_bgr)
            decision = None if (max(y_cnt, g_cnt) < MIN_PIXELS) else ("up" if y_cnt >= g_cnt else "down")
            return decision, y_cnt, g_cnt, mask_y, mask_g, frame_bgr

        # Score each candidate and pick best
        scores = []
        for tag, bgr in bgr_candidates:
            y_cnt, g_cnt, _, _ = _masks_from_bgr(bgr)
            scores.append((y_cnt + g_cnt, tag, bgr))
        scores.sort(reverse=True, key=lambda x: x[0])
        _, chosen_tag, frame_bgr = scores[0]
    else:
        # Already 3-channel; assume BGR
        frame_bgr = frame_raw if frame_raw.ndim == 3 else None
        if frame_bgr is None:
            return None, 0, 0, None, None, None

    # Build masks from the chosen BGR
    y_cnt, g_cnt, mask_y, mask_g = _masks_from_bgr(frame_bgr)
    decision = None if (max(y_cnt, g_cnt) < MIN_PIXELS) else ("up" if y_cnt >= g_cnt else "down")
    return decision, y_cnt, g_cnt, mask_y, mask_g, frame_bgr

# ===================== Overlay =====================
class ROIOverlay:
    """Transparent, click-through overlay drawing a red rectangle for the ROI."""
    def __init__(self, screen_w, screen_h):
        import tkinter as tk
        self.tk = tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.configure(bg="black")
        self.root.geometry(f"{screen_w}x{screen_h}+0+0")
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.rect_id = None

        # Click-through
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        WS_EX_TRANSPARENT = 0x20
        hwnd = self.root.winfo_id()
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                     windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE) |
                                     WS_EX_LAYERED | WS_EX_TRANSPARENT)

        self.running = False
        self.lock = threading.Lock()
        self._region = None

    def _tick(self):
        with self.lock:
            region = self._region
        if region:
            l, t, r, b = region
            if self.rect_id is not None:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(l, t, r, b, outline="red", width=3)
        if self.running:
            self.root.after(30, self._tick)

    def show(self, region):
        with self.lock:
            self._region = region
        if not self.running:
            self.running = True
            self.root.deiconify()
            self._tick()

    def update_region(self, region):
        with self.lock:
            self._region = region

    def hide(self):
        self.running = False
        self.root.withdraw()

# ===================== Preview helpers =====================
def get_monitor_geometry(index=0):
    """Return (x,y,w,h) for monitor index using screeninfo; falls back to (0,0,1920,1080)."""
    try:
        from screeninfo import get_monitors
        mons = get_monitors()
        if not mons: return (0, 0, 1920, 1080)
        if index < 0 or index >= len(mons): index = 0
        m = mons[index]
        return (m.x, m.y, m.width, m.height)
    except Exception:
        return (0, 0, 1920, 1080)

def letterbox(img, canvas_w, canvas_h):
    """Resize img to fit inside (canvas_w, canvas_h) with black bars."""
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    scale = min(canvas_w / w, canvas_h / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    x = (canvas_w - nw) // 2
    y = (canvas_h - nh) // 2
    canvas[y:y+nh, x:x+nw] = resized
    return canvas

# ===================== Auto-calibration =====================
def auto_calibrate(win, cap):
    """Scan bottom ~45% of window for yellow/green cluster and set ROI to its bbox."""
    left, top, right, bottom = win.left, win.top, win.right, win.bottom
    w, h = right - left, bottom - top
    scan_region = (left, top + int(h*0.55), right, bottom)

    frame_raw = cap.grab(scan_region)
    decision, _, _, mask_y, mask_g, frame_bgr = detect_prompt_auto(frame_raw)
    if frame_bgr is None:
        print("Auto-calibrate: no frame")
        return roi_from_window(win)

    mask = cv2.morphologyEx(cv2.bitwise_or(mask_y, mask_g), cv2.MORPH_OPEN, np.ones((3,3),np.uint8), iterations=1)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        print("Auto-calibrate: no yellow/green clusters found. Start a fishing prompt, then press F9 again.")
        return roi_from_window(win)

    c = max(cnts, key=cv2.contourArea)
    x,y,wc,hc = cv2.boundingRect(c)

    bx1 = scan_region[0] + x
    by1 = scan_region[1] + y
    bx2 = bx1 + wc
    by2 = by1 + hc

    pad = 10
    left0, top0, right0, bottom0 = win.left, win.top, win.right, win.bottom
    bx1 = max(left0,  bx1 - pad)
    by1 = max(top0,   by1 - pad)
    bx2 = min(right0, bx2 + pad)
    by2 = min(bottom0,by2 + pad)

    global ROI_X_MIN_PCT, ROI_X_MAX_PCT, ROI_Y_MIN_PCT, ROI_Y_MAX_PCT
    ROI_X_MIN_PCT = (bx1 - left0) / (right0 - left0)
    ROI_X_MAX_PCT = (bx2 - left0) / (right0 - left0)
    ROI_Y_MIN_PCT = (by1 - top0)  / (bottom0 - top0)
    ROI_Y_MAX_PCT = (by2 - top0)  / (bottom0 - top0)
    region = (bx1, by1, bx2, by2)
    print(f"Auto-calibrated ROI -> %: x=({ROI_X_MIN_PCT:.3f},{ROI_X_MAX_PCT:.3f}) y=({ROI_Y_MIN_PCT:.3f},{ROI_Y_MAX_PCT:.3f}) -> {region}")
    return region

# ===================== Main =====================
def print_help():
    print("""
Hotkeys (edge-triggered):
  Esc                Quit
  F8                 Toggle scanning on/off
  F3                 Toggle 1080p preview (on monitor index)
  F7                 Cycle preview monitor index
  F6                 Toggle transparent ROI overlay
  F9                 Auto-calibrate ROI (start a fishing prompt first)
  F5                 Save ROI to roi_config.json

While held (repeat):
  Alt + Arrow Keys         Move ROI by 1% per tick
  Ctrl + Alt + Arrows      Resize ROI edge by 1% per tick
""")

def main():
    print("Locating Warcraft III window...")
    win = find_wc3_window(WINDOW_TITLE_KEYWORD)
    print(f"Found: '{win.title}' at ({win.left},{win.top}) {win.width}x{win.height}")
    cap = Capture()
    region = roi_from_window(win)
    print_help()
    print(f"Starting ROI: {region}")

    # Flags/state
    scanning = True
    preview_on = False
    preview_initialized = False
    overlay = None
    should_exit = False
    overlay_toggle_requested = False
    autocal_requested = False
    save_requested = False
    cycle_monitor_requested = False

    # Detection state
    in_prompt = False
    clear_streak = 0
    last_decision = None
    last_press_ts = 0.0

    # --- Hotkeys (clean, no flicker) ---
    def toggle_preview():
        nonlocal preview_on, preview_initialized
        preview_on = not preview_on
        if not preview_on:
            try: cv2.destroyWindow(PREVIEW_WIN_NAME)
            except Exception: pass
            preview_initialized = False
        else:
            preview_initialized = False
            print(f"Preview: ON (monitor index {PREVIEW_MONITOR_INDEX})")

    def toggle_scanning():
        nonlocal scanning
        scanning = not scanning
        print(f"Scanning: {'ON' if scanning else 'OFF'}")

    def toggle_overlay():
        nonlocal overlay_toggle_requested
        overlay_toggle_requested = True

    def request_autocal():
        nonlocal autocal_requested
        autocal_requested = True

    def request_save():
        nonlocal save_requested
        save_requested = True

    def request_exit():
        nonlocal should_exit
        should_exit = True

    def cycle_preview_monitor():
        nonlocal cycle_monitor_requested
        cycle_monitor_requested = True

    keyboard.add_hotkey('f3', toggle_preview)
    keyboard.add_hotkey('f8', toggle_scanning)
    keyboard.add_hotkey('f6', toggle_overlay)
    keyboard.add_hotkey('f9', request_autocal)
    keyboard.add_hotkey('f5', request_save)
    keyboard.add_hotkey('esc', request_exit)
    keyboard.add_hotkey('f7', cycle_preview_monitor)

    # Try to focus WC3 once
    try: win.activate()
    except Exception: pass

    global PREVIEW_MONITOR_INDEX

    while True:
        if should_exit:
            print("Exiting.")
            break

        # Handle queued overlay toggle
        if overlay_toggle_requested:
            overlay_toggle_requested = False
            if overlay is None:
                import tkinter as tk
                rt = tk.Tk(); w = rt.winfo_screenwidth(); h = rt.winfo_screenheight(); rt.destroy()
                overlay = ROIOverlay(w, h)
            if overlay.running:
                overlay.hide(); print("Overlay: OFF")
            else:
                overlay.show(region); print("Overlay: ON")

        # Auto-calibration
        if autocal_requested:
            autocal_requested = False
            region = auto_calibrate(win, cap)
            if overlay and overlay.running:
                overlay.update_region(region)

        # Save ROI
        if save_requested:
            save_requested = False
            save_cfg({
                "ROI_X_MIN_PCT": ROI_X_MIN_PCT,
                "ROI_X_MAX_PCT": ROI_X_MAX_PCT,
                "ROI_Y_MIN_PCT": ROI_Y_MIN_PCT,
                "ROI_Y_MAX_PCT": ROI_Y_MAX_PCT,
            })
            print("Saved ROI to roi_config.json")

        # Cycle monitor index for preview
        if cycle_monitor_requested:
            cycle_monitor_requested = False
            try:
                from screeninfo import get_monitors
                mons = get_monitors()
                if mons:
                    PREVIEW_MONITOR_INDEX = (PREVIEW_MONITOR_INDEX + 1) % len(mons)
            except Exception:
                PREVIEW_MONITOR_INDEX = 0
            print(f"Preview monitor index -> {PREVIEW_MONITOR_INDEX}")
            preview_initialized = False

        # Live ROI nudging (hold keys)
        if keyboard.is_pressed("alt"):
            changed = False
            if keyboard.is_pressed("ctrl"):
                if keyboard.is_pressed("left"):  region = nudge_roi(win, resize='left');  changed=True
                if keyboard.is_pressed("right"): region = nudge_roi(win, resize='right'); changed=True
                if keyboard.is_pressed("up"):    region = nudge_roi(win, resize='up');    changed=True
                if keyboard.is_pressed("down"):  region = nudge_roi(win, resize='down');  changed=True
            else:
                dx=dy=0
                if keyboard.is_pressed("left"):  dx=-1
                if keyboard.is_pressed("right"): dx= 1
                if keyboard.is_pressed("up"):    dy=-1
                if keyboard.is_pressed("down"):  dy= 1
                if dx or dy:
                    region = nudge_roi(win, move=(dx,dy)); changed=True
            if changed and overlay and overlay.running:
                overlay.update_region(region)
            if changed:
                time.sleep(0.12)  # gentle repeat rate

        # ---------- Preview (uses auto color-fix) ----------
        if preview_on:
            frame_raw = cap.grab(region)
            decision_p, y_cnt_p, g_cnt_p, mask_y_p, mask_g_p, frame_bgr_p = detect_prompt_auto(frame_raw)
            if frame_bgr_p is not None:
                yb = cv2.cvtColor(mask_y_p, cv2.COLOR_GRAY2BGR)
                gb = cv2.cvtColor(mask_g_p, cv2.COLOR_GRAY2BGR)
                mosaic = np.hstack([frame_bgr_p, yb, gb])
                txt = f"UP(yellow)={y_cnt_p}  DOWN(green)={g_cnt_p}  decision={decision_p}"
                cv2.putText(mosaic, txt, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                canvas = letterbox(mosaic, PREVIEW_W, PREVIEW_H)

                if not preview_initialized:
                    try: cv2.destroyWindow(PREVIEW_WIN_NAME)
                    except Exception: pass
                    cv2.namedWindow(PREVIEW_WIN_NAME, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(PREVIEW_WIN_NAME, PREVIEW_W, PREVIEW_H)
                    mon_x, mon_y, mon_w, mon_h = get_monitor_geometry(PREVIEW_MONITOR_INDEX)
                    win_x = mon_x + (mon_w - PREVIEW_W) // 2
                    win_y = mon_y + (mon_h - PREVIEW_H) // 2
                    cv2.moveWindow(PREVIEW_WIN_NAME, win_x, win_y)
                    try: cv2.setWindowProperty(PREVIEW_WIN_NAME, cv2.WND_PROP_TOPMOST, 0)
                    except Exception: pass
                    preview_initialized = True

                cv2.imshow(PREVIEW_WIN_NAME, canvas)
                # Esc inside the preview window closes just the preview
                if cv2.waitKey(1) & 0xFF == 27:
                    preview_on = False
                    preview_initialized = False
                    try: cv2.destroyWindow(PREVIEW_WIN_NAME)
                    except Exception: pass
            else:
                time.sleep(0.01)

        # ---------- Detection & keypress (auto color-fix) ----------
        frame_raw = cap.grab(region)
        decision, y_cnt, g_cnt, mask_y, mask_g, frame_bgr = detect_prompt_auto(frame_raw)

        if not scanning:
            time.sleep(0.005)
            continue

        active_pixels = max(y_cnt, g_cnt)
        prompt_present = active_pixels >= MIN_PIXELS
        now = time.time()

        if prompt_present:
            # Rising-edge: new prompt just appeared
            if not in_prompt:
                # First frame of the new prompt => press immediately
                key = "up" if (y_cnt >= g_cnt) else "down"
                if now - last_press_ts >= COOLDOWN_SEC:
                    time.sleep(random.uniform(*RANDOM_JITTER_SEC))
                    keyboard.press_and_release(key)
                    last_press_ts = time.time()
                    last_decision = key
                in_prompt = True
                clear_streak = 0
            else:
                # Still inside a visible prompt; if it flips UP<->DOWN without clearing, allow re-press
                key = "up" if (y_cnt >= g_cnt) else "down"
                if key != last_decision and (now - last_press_ts) >= COOLDOWN_SEC:
                    time.sleep(random.uniform(*RANDOM_JITTER_SEC))
                    keyboard.press_and_release(key)
                    last_press_ts = time.time()
                    last_decision = key
                clear_streak = 0
        else:
            # No prompt (or too few pixels) — build up a clear streak
            if in_prompt:
                clear_streak += 1
                if clear_streak >= CLEAR_FRAMES:
                    in_prompt = False
                    last_decision = None
                    clear_streak = 0

        time.sleep(0.005)

    # Cleanup
    try: cv2.destroyAllWindows()
    except Exception: pass
    if overlay and overlay.running:
        overlay.hide()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[Error] {e}")
        sys.exit(1)
