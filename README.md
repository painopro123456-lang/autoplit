# Autoplit — Formula Apex Racing

Experimental visual-driving prototype for Roblox Formula Apex Racing.

## What it does
- Finds the Roblox window by window title or `RobloxPlayerBeta.exe`.
- Captures the Roblox client area only (PrintWindow first, visible-window fallback).
- Detects approximate road edges using OpenCV and applies proportional A/D steering.
- Uses W for throttle and S to brake when lane detection is lost.

## Controls
- **F6** — toggle autopilot
- **F7** — emergency stop
- **F8** — quit
- **Ctrl+C** — quit

## Run from source
1. Install 64-bit Python 3.10 or newer.
2. In this folder run:
   ```powershell
   py -m pip install -r requirements.txt
   py autopilot.py
   ```
3. Open Formula Apex Racing in Roblox. Press F6 to enable.
4. Keep Roblox as the active window while it drives.

## Important limitations
This is an experimental computer-vision prototype, not a validated racing bot. Road-edge detection depends on the track, camera angle, lighting, and HUD. It may steer incorrectly; test at low speed in a safe/private session and be ready to press F7. The PrintWindow capture path may return a blank image with some Roblox rendering modes; the fallback captures the Roblox screen rectangle and can be obscured by other windows. Windows generally requires the game to be foreground for keyboard input to control it.

## Build
A GitHub Actions workflow builds a Windows executable on each push. Download the `Autoplit-Windows` artifact from the workflow run.
