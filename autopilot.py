import ctypes
import sys
import time
from ctypes import wintypes

import cv2
import numpy as np
import pydirectinput
import win32gui
import win32process
import psutil

TITLE_HINTS = ("roblox",)
PROCESS_HINTS = ("robloxplayerbeta.exe",)
KEY_LEFT, KEY_RIGHT, KEY_THROTTLE, KEY_BRAKE = "a", "d", "w", "s"

user32 = ctypes.windll.user32
PW_RENDERFULLCONTENT = 0x00000002


def find_roblox_window():
    matches = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).lower()
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid).name().lower()
        except (psutil.Error, win32gui.error):
            process = ""
        if any(h in title for h in TITLE_HINTS) or process in PROCESS_HINTS:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            if right - left > 250 and bottom - top > 180:
                matches.append(hwnd)

    win32gui.EnumWindows(callback, None)
    return matches[0] if matches else None


def capture_window(hwnd):
    left, top = win32gui.ClientToScreen(hwnd, (0, 0))
    client = win32gui.GetClientRect(hwnd)
    right, bottom = win32gui.ClientToScreen(hwnd, (client[2], client[3]))
    width, height = right - left, bottom - top
    if width < 250 or height < 180:
        return None

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    import win32ui
    src = win32ui.CreateDCFromHandle(hwnd_dc)
    mem = src.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(src, width, height)
    mem.SelectObject(bmp)
    result = user32.PrintWindow(hwnd, mem.GetSafeHdc(), PW_RENDERFULLCONTENT)
    info = bmp.GetInfo()
    bits = bmp.GetBitmapBits(True)
    frame = np.frombuffer(bits, dtype=np.uint8).reshape(
        (info["bmHeight"], info["bmWidth"], 4)
    )
    win32gui.DeleteObject(bmp.GetHandle())
    mem.DeleteDC()
    src.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    if result == 1 and frame.size and np.mean(frame[:, :, :3]) > 3:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    import mss
    with mss.mss() as sct:
        shot = np.array(sct.grab({
            "left": left, "top": top, "width": width, "height": height
        }))
    return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)


def lane_error(frame):
    h, w = frame.shape[:2]
    roi = frame[int(h * 0.48):h, :]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 55, 145)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=35,
        minLineLength=max(28, w // 16), maxLineGap=45
    )
    if lines is None:
        return None, 0.0

    left_x, right_x = [], []
    rh = roi.shape[0]
    for item in lines[:, 0]:
        x1, y1, x2, y2 = map(int, item)
        dx, dy = x2 - x1, y2 - y1
        if abs(dx) < 4:
            continue
        slope = dy / dx
        if abs(slope) < 0.28:
            continue
        xb = x1 + (rh - y1) * dx / dy if dy else x1
        if slope < 0 and xb < w * 0.62:
            left_x.append(xb)
        elif slope > 0 and xb > w * 0.38:
            right_x.append(xb)

    if not left_x or not right_x:
        return None, 0.0
    left = float(np.median(left_x))
    right = float(np.median(right_x))
    if right - left < w * 0.18 or right - left > w * 0.95:
        return None, 0.0
    lane_center = (left + right) / 2
    error = (lane_center - w / 2) / (w / 2)
    confidence = min(1.0, (len(left_x) + len(right_x)) / 6)
    return float(np.clip(error, -1, 1)), confidence


def release_all():
    for key in (KEY_LEFT, KEY_RIGHT, KEY_THROTTLE, KEY_BRAKE):
        pydirectinput.keyUp(key)


def main():
    print("Formula Apex Racing Autopilot — experimental visual prototype")
    print("F6 = enable/disable, F7 = emergency stop, F8 = quit.")
    print("Roblox must be the active window for keyboard driving.")
    enabled = False
    last_steer = None
    hwnd = None
    pydirectinput.PAUSE = 0

    try:
        while True:
            if hwnd is None or not win32gui.IsWindow(hwnd):
                hwnd = find_roblox_window()
                if hwnd:
                    print("Roblox window detected.")
                else:
                    print("Waiting for Roblox...")
                    time.sleep(1)
                    continue

            if user32.GetAsyncKeyState(0x75) & 1:
                enabled = not enabled
                release_all()
                last_steer = None
                print("Autopilot", "ON" if enabled else "OFF")
            if user32.GetAsyncKeyState(0x76) & 1:
                enabled = False
                release_all()
                last_steer = None
                print("Emergency stop.")
            if user32.GetAsyncKeyState(0x77) & 1:
                break

            frame = capture_window(hwnd)
            if frame is None:
                time.sleep(0.1)
                continue

            if enabled:
                if user32.GetForegroundWindow() != hwnd:
                    release_all()
                    last_steer = None
                    print("\rRoblox detected; click the Roblox game window to drive. ", end="")
                else:
                    error, confidence = lane_error(frame)
                    if error is None or confidence < 0.25:
                        release_all()
                        last_steer = None
                        pydirectinput.keyDown(KEY_BRAKE)
                        print("\rTrack edges not detected — braking for safety.             ", end="")
                    else:
                        # A lane center to the right means steer right (D), and vice versa.
                        steer = "d" if error > 0.10 else "a" if error < -0.10 else None
                        if steer != last_steer:
                            if last_steer:
                                pydirectinput.keyUp(last_steer)
                            if steer:
                                pydirectinput.keyDown(steer)
                            last_steer = steer
                        pydirectinput.keyUp(KEY_BRAKE)
                        pydirectinput.keyDown(KEY_THROTTLE)
                        print(f"\rDriving | lane error {error:+.2f} | confidence {confidence:.1f}     ", end="")
            else:
                release_all()
                last_steer = None
            time.sleep(0.035)
    except KeyboardInterrupt:
        pass
    finally:
        release_all()
        print("\nAutopilot stopped.")


if __name__ == "__main__":
    main()
