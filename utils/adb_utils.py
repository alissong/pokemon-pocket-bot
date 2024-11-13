# utils/adb_utils.py

import os
import subprocess
import time
from threading import Thread

import cv2


def get_input_device():
    try:
        # First check if we can access the devices list
        result = subprocess.run(
            ["adb", "shell", "cat", "/proc/bus/input/devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # Look for the virtual input device that handles both kbd and mouse
            lines = result.stdout.splitlines()
            current_device = None
            for line in lines:
                if line.startswith("N: Name="):
                    if "input" in line.lower():
                        current_device = "/dev/input/event2"
                        break

            if current_device:
                return current_device

        # Fallback to event2 as it's the known working device from the device list
        return "/dev/input/event2"

    except Exception as e:
        print(f"Error finding input device: {e}")
        return "/dev/input/event2"  # Default to event2 based on your device list


def connect_to_emulator(emulator_name):
    subprocess.run(["adb", "connect", emulator_name])


def take_screenshot(screenshot_object_receiver=None):
    screenshot_path = os.path.join("images", "screenshot.png")
    try:
        subprocess.run(
            ["adb", "shell", "screencap", "/sdcard/screenshot.png"], timeout=5
        )
        subprocess.run(
            ["adb", "pull", "/sdcard/screenshot.png", screenshot_path], timeout=5
        )
        screenshot = cv2.imread(screenshot_path)
        if screenshot_object_receiver:
            screenshot_object_receiver.last_screenshot = screenshot
        return screenshot
    except subprocess.TimeoutExpired:
        print("ADB command timed out. Emulator may be unresponsive.")
        return None
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None


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


def send_event(device, type, code, value):
    subprocess.run(
        ["adb", "shell", "sendevent", device, str(type), str(code), str(value)]
    )


def drag_points(points, duration=1.0, device=None):
    """
    Perform a drag operation through multiple points.

    Args:
        points: List of (x, y) tuples representing the points to drag through
        duration: Total duration of the entire drag operation in seconds
        device: The input device path (will be auto-detected if None)
    """
    if device is None:
        device = get_input_device()  # Confirm this resolves correctly

    if len(points) < 2:
        raise ValueError("At least 2 points are required for a drag operation")

    # Delay between points
    delay = duration / (len(points) - 1)

    # Start the touch
    send_event(device, 3, 57, 0)  # EV_ABS, ABS_MT_TRACKING_ID, 0
    x, y = points[0]
    send_event(device, 3, 53, x)  # EV_ABS, ABS_MT_POSITION_X, x
    send_event(device, 3, 54, y)  # EV_ABS, ABS_MT_POSITION_Y, y
    send_event(device, 0, 0, 0)  # EV_SYN, SYN_REPORT, 0
    print(f"Start at ({x}, {y})")  # Debug log

    time.sleep(delay)

    # Move through intermediate points
    for i, (x, y) in enumerate(points[1:], start=1):
        send_event(device, 3, 53, x)  # EV_ABS, ABS_MT_POSITION_X, x
        send_event(device, 3, 54, y)  # EV_ABS, ABS_MT_POSITION_Y, y
        send_event(device, 0, 0, 0)  # EV_SYN, SYN_REPORT, 0
        print(f"Move to ({x}, {y}), point {i}")  # Debug log
        time.sleep(delay)

    # End the touch
    send_event(device, 3, 57, -1)  # EV_ABS, ABS_MT_TRACKING_ID, -1
    send_event(device, 0, 0, 0)  # EV_SYN, SYN_REPORT, 0
    print("End touch")  # Debug log


def drag_first_y(start_pos, end_pos, duration=0.5, debug_window=None, screenshot=None):
    """
    Performs a drag operation through three sequential touch points.
    """
    x1, y1 = start_pos
    x3, y3 = end_pos
    # Second point keeps x1 but uses y3 (vertical movement first)
    x2, y2 = x1, y3

    points = [(x1, y1), (x2, y2), (x3, y3)]
    # Log the action if debug window is available
    if debug_window and debug_window.window is not None:
        if screenshot is None:
            screenshot = take_screenshot()
        action_coords = {"type": "drag_first_y", "coords": points}
        points_str = " -> ".join([f"({x}, {y})" for x, y in points])
        debug_window.log_action(
            f"Drag through points: {points_str}", screenshot, action_coords
        )
    drag_points(points, duration)
