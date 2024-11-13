# src/controllers/emulator_controller.py

import os
import subprocess
import time

from utils.adb_utils import connect_to_emulator


class EmulatorController:
    def __init__(self, app_state, log_callback):
        self.app_state = app_state
        self.log_callback = log_callback

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
                self.log_callback("No emulator devices found.")
                return None
        except Exception as e:
            self.log_callback(f"Error getting emulator name: {e}")
            return None

    def connect_and_run(self):
        if self.app_state.emulator_name:
            connect_to_emulator(self.app_state.emulator_name)
        else:
            emulator_name = self.get_emulator_name()
            if emulator_name:
                connect_to_emulator(emulator_name)
                self.log_callback("Connected to emulator")
            else:
                self.log_callback("Failed to connect to emulator.")

    def restart_emulator(self):
        try:
            self.log_callback("Closing emulator...")
            subprocess.run(["adb", "shell", "reboot"])
            time.sleep(5)
            self.log_callback("Starting emulator...")
            emulator_path = self.app_state.program_path
            if emulator_path:
                # Adjust the command based on how you start your emulator
                subprocess.Popen([os.path.join(emulator_path, "dnplayer.exe")])
                time.sleep(10)  # Wait for emulator to start
            else:
                self.log_callback("Emulator path not set. Cannot restart emulator.")
        except Exception as e:
            self.log_callback(f"Error restarting emulator: {e}")
