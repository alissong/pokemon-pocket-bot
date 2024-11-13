# utils/adb_utils.py

import os
import subprocess
import time
from threading import Thread

import cv2


def connect_to_emulator(emulator_name):
    subprocess.run(["adb", "connect", emulator_name])


def take_screenshot(screenshot_object_receiver=None):
    screenshot_path = os.path.join("images", "screenshot.png")
    subprocess.run(["adb", "shell", "screencap", "/sdcard/screenshot.png"])
    subprocess.run(["adb", "pull", "/sdcard/screenshot.png", screenshot_path])
    screenshot = cv2.imread(screenshot_path)
    if screenshot_object_receiver:
        screenshot_object_receiver.last_screenshot = screenshot
    return screenshot


def click_position(x, y, debug_window=None, screenshot=None):
    if debug_window and debug_window.window is not None:
        if screenshot is None:
            screenshot = take_screenshot()
        action_coords = {"type": "click", "coords": (x, y)}
        debug_window.log_action(f"Click at ({x}, {y})", screenshot, action_coords)
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])


def find_subimage(screenshot, subimage):
    result = cv2.matchTemplate(screenshot, subimage, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_loc, max_val


def long_press_position(x, y, duration=1.0):
    screenshot = None

    def capture_screenshot_during_press():
        nonlocal screenshot
        time.sleep(duration * 0.5)
        screenshot = take_screenshot()

    screenshot_thread = Thread(target=capture_screenshot_during_press)
    screenshot_thread.start()

    subprocess.run(
        [
            "adb",
            "shell",
            "input",
            "swipe",
            str(x),
            str(y),
            str(x),
            str(y),
            str(int(duration * 1000)),
        ]
    )

    screenshot_thread.join()

    return screenshot


def drag_position(start_pos, end_pos, duration=0.5, debug_window=None, screenshot=None):
    start_x, start_y = start_pos
    end_x, end_y = end_pos
    if debug_window and debug_window.window is not None:
        if screenshot is None:
            screenshot = take_screenshot()
        action_coords = {"type": "drag", "coords": (start_x, start_y, end_x, end_y)}
        debug_window.log_action(
            f"Drag from ({start_x}, {start_y}) to ({end_x}, {end_y})",
            screenshot,
            action_coords,
        )

    duration_ms = int(duration * 1000)

    subprocess.run(
        [
            "adb",
            "shell",
            "input",
            "swipe",
            str(start_x),
            str(start_y),
            str(end_x),
            str(end_y),
            str(duration_ms),
        ]
    )
