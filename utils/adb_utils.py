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


def drag_points(points, duration=1.0, debug_window=None, screenshot=None):
    """
    Perform a drag operation through multiple points.

    Args:
        points: List of (x, y) tuples representing the points to drag through
        duration: Total duration of the entire drag operation in seconds
        debug_window: Debug window object for logging
        screenshot: Optional screenshot for debug logging
    """
    if len(points) < 2:
        raise ValueError("At least 2 points are required for a drag operation")

    # Log the action if debug window is available
    if debug_window and debug_window.window is not None:
        if screenshot is None:
            screenshot = take_screenshot()
        action_coords = {"type": "multipoint_drag", "coords": points}
        points_str = " -> ".join([f"({x}, {y})" for x, y in points])
        debug_window.log_action(
            f"Drag through points: {points_str}", screenshot, action_coords
        )

    # Calculate duration for each segment
    segment_duration = duration / (len(points) - 1)
    segment_duration_ms = int(segment_duration * 1000)

    # Perform drag operations through each consecutive pair of points
    for i in range(len(points) - 1):
        start_x, start_y = points[i]
        end_x, end_y = points[i + 1]

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
                str(segment_duration_ms),
            ]
        )


def drag_first_y(start_pos, end_pos, duration=0.5, debug_window=None, screenshot=None):
    """
    Performs a drag operation by moving vertically first, then horizontally.

    Args:
        start_pos: Tuple of (start_x, start_y)
        end_pos: Tuple of (end_x, end_y)
        duration: Duration of the drag in seconds
        debug_window: Debug window object for logging
        screenshot: Optional screenshot for debug logging
    """
    start_x, start_y = start_pos
    end_x, end_y = end_pos
    duration_ms = int((duration * 1000) / 2)  # Split duration between the two movements

    # Log the action if debug window is available
    if debug_window and debug_window.window is not None:
        if screenshot is None:
            screenshot = take_screenshot()
        intermediate_point = (start_x, end_y)
        points = [start_pos, intermediate_point, end_pos]
        action_coords = {"type": "drag_first_y", "coords": points}
        points_str = " -> ".join([f"({x}, {y})" for x, y in points])
        debug_window.log_action(
            f"Drag Y-first through points: {points_str}", screenshot, action_coords
        )

    # First move: Vertical (y-axis)
    intermediate_point = (start_x, end_y)

    # Execute both movements sequentially without shell quotes
    command = (
        f"adb shell input swipe {start_x} {start_y} {intermediate_point[0]} {intermediate_point[1]} {duration_ms} "
        f"& adb shell input swipe {intermediate_point[0]} {intermediate_point[1]} {end_x} {end_y} {duration_ms}"
    )
    subprocess.run(command, shell=True)
