"""
╔══════════════════════════════════════════════════════╗
║        HAND GESTURE VOLUME CONTROL                   ║
║        Tony Stark UI — MediaPipe + pycaw             ║
╚══════════════════════════════════════════════════════╝

INSTALL DEPENDENCIES:
    pip install opencv-python mediapipe pycaw comtypes numpy

CONTROLS:
    • Pinch thumb + index finger to set volume
      (closer = lower, farther = higher)
    • Press 'q' to quit
    • Press 'm' to toggle mute
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math

# ── pycaw (Windows only) ──────────────────────────────────────────────────────
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
    vol_range = volume_ctrl.GetVolumeRange()   # (min_dB, max_dB, step)
    MIN_VOL, MAX_VOL = vol_range[0], vol_range[1]
    PYCAW_AVAILABLE = True
    print("[✓] pycaw loaded — system volume control active")
except Exception as e:
    PYCAW_AVAILABLE = False
    MIN_VOL, MAX_VOL = -65.25, 0.0
    print(f"[!] pycaw not available ({e}). Running in demo mode (volume not changed).")


# ── MediaPipe setup ───────────────────────────────────────────────────────────
# Supports both old API (mp.solutions) and new modular API (mediapipe 0.10+)
try:
    mp_hands = mp.solutions.hands
    mp_draw  = mp.solutions.drawing_utils
    lm_spec   = mp_draw.DrawingSpec(color=(0, 140, 255), thickness=2, circle_radius=4)
    conn_spec = mp_draw.DrawingSpec(color=(0, 80, 180),  thickness=2)
    USE_LEGACY_API = True
    print("[✓] MediaPipe legacy API (mp.solutions)")
except AttributeError:
    # mediapipe 0.10+ on some platforms exposes the module differently
    import importlib
    _hands_mod = importlib.import_module("mediapipe.python.solutions.hands")
    _draw_mod  = importlib.import_module("mediapipe.python.solutions.drawing_utils")
    mp_hands  = _hands_mod
    mp_draw   = _draw_mod
    lm_spec   = _draw_mod.DrawingSpec(color=(0, 140, 255), thickness=2, circle_radius=4)
    conn_spec = _draw_mod.DrawingSpec(color=(0, 80, 180),  thickness=2)
    USE_LEGACY_API = False
    print("[✓] MediaPipe new modular API")

# ── Constants & state ─────────────────────────────────────────────────────────
SMOOTH_FACTOR   = 5        # frames to average for smoothing
HAND_DIST_MIN   = 30       # px — minimum pinch distance (maps to 0 %)
HAND_DIST_MAX   = 220      # px — maximum pinch distance (maps to 100 %)

vol_history     = []
current_vol_pct = 50.0
muted           = False
fps_history     = []
prev_time       = time.time()


def draw_hud(frame, vol_pct, muted, fps, dist, hand_present):
    h, w = frame.shape[:2]

    overlay = frame.copy()

    # ── corner brackets (Iron Man HUD style) ─────────────────────────────────
    blen = 30
    bt   = 2
    col  = (0, 200, 255)

    corners = [(20, 20), (w - 20, 20), (20, h - 20), (w - 20, h - 20)]
    for cx, cy in corners:
        sx = 1 if cx < w // 2 else -1
        sy = 1 if cy < h // 2 else -1
        cv2.line(overlay, (cx, cy), (cx + sx * blen, cy), col, bt)
        cv2.line(overlay, (cx, cy), (cx, cy + sy * blen), col, bt)

    # ── vertical volume bar (right side) ─────────────────────────────────────
    bar_x, bar_y, bar_w, bar_h = w - 55, 80, 20, h - 160
    # background
    cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  (20, 20, 20), -1)
    # fill
    if not muted:
        fill_h  = int(bar_h * vol_pct / 100)
        fill_y  = bar_y + bar_h - fill_h
        # gradient-ish: green→yellow→red
        r = int(255 * vol_pct / 100)
        g = int(255 * (1 - vol_pct / 100))
        cv2.rectangle(overlay, (bar_x, fill_y), (bar_x + bar_w, bar_y + bar_h),
                      (0, g, r), -1)
    # border
    cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  col, 1)
    # label
    cv2.putText(overlay, "VOL", (bar_x - 2, bar_y - 10),
                cv2.FONT_HERSHEY_DUPLEX, 0.45, col, 1)

    # ── volume percentage text ────────────────────────────────────────────────
    vol_str = "MUTE" if muted else f"{int(vol_pct):3d}%"
    cv2.putText(overlay, vol_str, (bar_x - 10, bar_y + bar_h + 22),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 200, 255), 1)

    # ── FPS counter ───────────────────────────────────────────────────────────
    cv2.putText(overlay, f"FPS {fps:2d}", (25, h - 25),
                cv2.FONT_HERSHEY_DUPLEX, 0.45, (100, 100, 100), 1)

    # ── status line ───────────────────────────────────────────────────────────
    status = "TRACKING" if hand_present else "SCANNING..."
    s_col  = (0, 255, 150) if hand_present else (0, 120, 255)
    cv2.putText(overlay, status, (25, 45),
                cv2.FONT_HERSHEY_DUPLEX, 0.6, s_col, 1)

    # ── distance readout ─────────────────────────────────────────────────────
    if hand_present:
        cv2.putText(overlay, f"DIST {int(dist):3d}px", (25, 70),
                    cv2.FONT_HERSHEY_DUPLEX, 0.45, (150, 150, 150), 1)

    # ── mute indicator ────────────────────────────────────────────────────────
    if muted:
        cv2.putText(overlay, "[ MUTED ]", (w // 2 - 55, 35),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 60, 255), 2)

    # ── title ─────────────────────────────────────────────────────────────────
    cv2.putText(overlay, "STARK AUDIO v1.0", (w // 2 - 85, h - 25),
                cv2.FONT_HERSHEY_DUPLEX, 0.45, (60, 60, 60), 1)

    # blend overlay
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    return frame


def draw_pinch_line(frame, p1, p2, vol_pct):
    """Draw the pinch connection with a glowing effect."""
    # glow layers
    for thickness, alpha_col in [(12, (0, 40, 80)), (6, (0, 100, 180)), (2, (0, 200, 255))]:
        cv2.line(frame, p1, p2, alpha_col, thickness)

    # midpoint circle
    mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
    cv2.circle(frame, mid, 12, (0, 200, 255), 2)
    cv2.circle(frame, mid, 4,  (255, 255, 255), -1)

    # distance arc hint
    dist = int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    cv2.putText(frame, f"{dist}px", (mid[0] + 14, mid[1] - 8),
                cv2.FONT_HERSHEY_DUPLEX, 0.4, (0, 200, 255), 1)


def set_system_volume(vol_pct):
    if not PYCAW_AVAILABLE:
        return
    vol_db = MIN_VOL + (MAX_VOL - MIN_VOL) * (vol_pct / 100.0)
    volume_ctrl.SetMasterVolumeLevel(vol_db, None)


def toggle_mute():
    global muted
    if PYCAW_AVAILABLE:
        muted = not muted
        volume_ctrl.SetMute(int(muted), None)
    else:
        muted = not muted


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    global current_vol_pct, muted, prev_time, vol_history, fps_history


    
    cap = cv2.VideoCapture("http://192.168.100.132:4747/video")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("[✗] Cannot open webcam.")
        return

    with mp_hands.Hands(
        model_complexity=0,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    ) as hands:

        print("\n[✓] STARK AUDIO ONLINE")
        print("    • Pinch THUMB + INDEX to control volume")
        print("    • Press 'm' to mute/unmute")
        print("    • Press 'q' to quit\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ── FPS ──────────────────────────────────────────────────────────
            now      = time.time()
            fps_history.append(1 / max(now - prev_time, 1e-6))
            if len(fps_history) > 10:
                fps_history.pop(0)
            fps      = int(np.mean(fps_history))
            prev_time = now

            # ── Process ───────────────────────────────────────────────────────
            rgb.flags.writeable = False
            results = hands.process(rgb)
            rgb.flags.writeable = True

            hand_present = False
            dist         = 0.0

            if results.multi_hand_landmarks:
                hand_present = True
                lm = results.multi_hand_landmarks[0]

                # Draw skeleton
                mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS,
                                       lm_spec, conn_spec)

                h_px, w_px = frame.shape[:2]

                # Thumb tip (4) and Index tip (8)
                thumb = lm.landmark[4]
                index = lm.landmark[8]

                tx, ty = int(thumb.x * w_px), int(thumb.y * h_px)
                ix, iy = int(index.x * w_px), int(index.y * h_px)

                dist = math.hypot(ix - tx, iy - ty)

                # Highlight fingertips
                cv2.circle(frame, (tx, ty), 10, (0, 255, 200), -1)
                cv2.circle(frame, (ix, iy), 10, (0, 255, 200), -1)
                cv2.circle(frame, (tx, ty), 14, (0, 200, 255), 2)
                cv2.circle(frame, (ix, iy), 14, (0, 200, 255), 2)

                draw_pinch_line(frame, (tx, ty), (ix, iy), current_vol_pct)

                # Map distance → volume %
                raw_pct = np.interp(dist,
                                    [HAND_DIST_MIN, HAND_DIST_MAX],
                                    [0, 100])
                raw_pct = float(np.clip(raw_pct, 0, 100))

                # Smooth
                vol_history.append(raw_pct)
                if len(vol_history) > SMOOTH_FACTOR:
                    vol_history.pop(0)
                current_vol_pct = float(np.mean(vol_history))

                if not muted:
                    set_system_volume(current_vol_pct)

            # ── Draw HUD ──────────────────────────────────────────────────────
            frame = draw_hud(frame, current_vol_pct, muted, fps, dist, hand_present)

            cv2.imshow("STARK AUDIO — Hand Volume Control", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'):
                toggle_mute()
                print(f"[~] {'MUTED' if muted else 'UNMUTED'}")

    cap.release()
    cv2.destroyAllWindows()
    print("[✓] Session ended.")


if __name__ == "__main__":
    main()