# utils/adb_utils.py

import os
import subprocess
import time
from threading import Thread

import cv2


def connect_to_emulator(emulator_name):
    subprocess.run(["adb", "connect", emulator_name])


def take_screenshot():
    screenshot_path = os.path.join("images", "screenshot.png")
    subprocess.run(["adb", "shell", "screencap", "/sdcard/screenshot.png"])
    subprocess.run(["adb", "pull", "/sdcard/screenshot.png", screenshot_path])
    return cv2.imread(screenshot_path)


def click_position(x, y):
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


def drag_position(start_pos, end_pos, duration=0.5):
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    duration_ms = int(duration * 500)

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
