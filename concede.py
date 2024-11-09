import subprocess
import threading
import time

from adb_utils import (
    click_position,
    connect_to_emulator,
    find_subimage,
    take_screenshot,
)
from loaders import load_template_images


class PokemonConcedeBot:
    def __init__(self, app_state, log_callback):
        self.app_state = app_state
        self.log_callback = log_callback
        self.running = False
        self.template_images = load_template_images("images")

        self.turn_check_region = (50, 1560, 200, 20)
        self.card_start_x = 500
        self.card_y = 1500
        self.card_offset_x = 60
        self.zoom_card_region = (200, 360, 570, 400)

    def start(self):
        if not self.app_state.program_path:
            self.log_callback("Please select emulator path first.")
            return
        self.running = True
        threading.Thread(target=self.connect_and_run).start()

    def stop(self):
        self.running = False

    def connect_and_run(self):
        if self.app_state.emulator_name:
            connect_to_emulator(self.app_state.emulator_name)
        else:
            emulator_name = self.get_emulator_name()
            connect_to_emulator(emulator_name)
        self.log_callback("Connected to emulator")
        self.run_script()

    def get_emulator_name(self):
        try:
            result = subprocess.run(
                ["adb", "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            output = result.stdout

            lines = output.splitlines()

            devices = [line.split("\t")[0] for line in lines[1:] if "device" in line]

            if devices:
                return devices[0]
            else:
                return None
        except Exception as e:
            print(f"Error getting emulator name: {e}")
            return None

    def run_script(self):
        while self.running:
            screenshot = take_screenshot()

            if not self.check_and_click(
                screenshot,
                self.template_images["BATTLE_ALREADY_SCREEN"],
                "Battle already screen",
            ):
                self.check_and_click(
                    screenshot, self.template_images["BATTLE_SCREEN"], "Battle screen"
                )
            time.sleep(1)
            self.perform_search_battle_actions()
            self.perform_concede_actions()

    def perform_search_battle_actions(self):
        for key in [
            "VERSUS_SCREEN",
            "RANDOM_MATCH_SCREEN",
            "BATTLE_BUTTON",
        ]:
            if not self.check_and_click_until_found(
                self.template_images[key], f"{key.replace('_', ' ').title()}"
            ):
                break

    def perform_concede_actions(self):
        for key in [
            "MATCH_MENU_BUTTON",
            "CONCEDE_BUTTON",
            "CONCEDE_ACCEPT_BUTTON",
            "TAP_TO_PROCEED_BUTTON",
            "NEXT_BUTTON",
            "THANKS_BUTTON",
        ]:
            if not self.check_and_click_until_found(
                self.template_images[key], f"{key.replace('_', ' ').title()}"
            ):
                break
        time.sleep(2)
        self.check_and_click_until_found(
            self.template_images["CROSS_BUTTON"], "Cross button"
        )
        time.sleep(4)

    def check(self, screenshot, template_image, log_message, similarity_threshold=0.8):
        _, similarity = find_subimage(screenshot, template_image)
        log_message = (
            f"{log_message} found - {similarity:.2f}"
            if similarity > similarity_threshold
            else f"{log_message} NOT found - {similarity:.2f}"
        )
        self.log_callback(log_message)
        return similarity > similarity_threshold

    def check_and_click(
        self, screenshot, template_image, log_message, similarity_threshold=0.8
    ):
        position, similarity = find_subimage(screenshot, template_image)
        if similarity > similarity_threshold:
            self.log_and_click(position, f"{log_message} found - {similarity:.2f}")
            return True
        else:
            self.log_callback(f"{log_message} NOT found - {similarity:.2f}")
            return False

    def check_and_click_until_found(
        self, template_image, log_message, similarity_threshold=0.8, timeout=30
    ):
        start_time = time.time()
        attempts = 0
        max_attempts = 10

        while self.running:
            screenshot = take_screenshot()
            position, similarity = find_subimage(screenshot, template_image)
            self.log_callback(f"Searching... {log_message} - {similarity:.2f}")

            if similarity > similarity_threshold:
                self.log_and_click(position, f"{log_message} found - {similarity:.2f}")
                return True
            elif time.time() - start_time > timeout:
                attempts += 1
                self.log_callback(
                    f"{log_message} not found within timeout. Attempt {attempts}/{max_attempts}."
                )
                if attempts >= max_attempts:
                    self.log_callback("Max attempts reached. Stopping the bot.")
                    self.stop()
                return False
            else:
                time.sleep(0.5)

    def log_and_click(self, position, message):
        self.log_callback(message)
        click_position(position[0], position[1])
