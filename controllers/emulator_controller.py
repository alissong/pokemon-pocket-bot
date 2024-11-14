# src/controllers/emulator_controller.py

import os
import subprocess
import time


class EmulatorController:
    def __init__(self, app_state, log_callback):
        self.app_state = app_state
        self.log_callback = log_callback
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 5  # seconds

    def wait_for_device(self, timeout=60):
        """Wait for device to be fully online and responsive"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["adb", "wait-for-device"],
                    timeout=10,
                    capture_output=True,
                    text=True,
                )

                # Check if device is actually responsive
                result = subprocess.run(
                    ["adb", "shell", "getprop", "sys.boot_completed"],
                    timeout=5,
                    capture_output=True,
                    text=True,
                )

                if result.stdout.strip() == "1":
                    return True

            except subprocess.TimeoutExpired:
                self.log_callback("Waiting for device to become responsive...")
            except Exception as e:
                self.log_callback(f"Error while waiting for device: {e}")

            time.sleep(2)

        return False

    def get_emulator_name(self):
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],  # Added -l for more detailed output
                timeout=10,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.log_callback(f"ADB command failed: {result.stderr}")
                return None

            lines = result.stdout.splitlines()
            devices = []

            for line in lines[1:]:  # Skip the first line (header)
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        state = parts[1]
                        devices.append((device_id, state))

            if not devices:
                self.log_callback("No devices found")
                return None

            # Check for offline devices
            offline_devices = [d[0] for d in devices if d[1] == "offline"]
            if offline_devices:
                self.log_callback(f"Found offline devices: {offline_devices}")
                self.handle_offline_devices(offline_devices)

            # Return first online device
            online_devices = [d[0] for d in devices if d[1] == "device"]
            return online_devices[0] if online_devices else None

        except subprocess.TimeoutExpired:
            self.log_callback("ADB command timed out")
            return None
        except Exception as e:
            self.log_callback(f"Error getting emulator name: {e}")
            return None

    def handle_offline_devices(self, device_ids):
        """Handle offline devices by killing ADB server and reconnecting"""
        self.log_callback("Attempting to recover offline devices...")
        try:
            # Kill ADB server
            subprocess.run(["adb", "kill-server"], timeout=5)
            time.sleep(2)

            # Start ADB server
            subprocess.run(["adb", "start-server"], timeout=5)
            time.sleep(2)

            # Try to reconnect to each device
            for device_id in device_ids:
                subprocess.run(["adb", "disconnect", device_id], timeout=5)
                time.sleep(1)
                subprocess.run(["adb", "connect", device_id], timeout=5)

        except Exception as e:
            self.log_callback(f"Error during offline device recovery: {e}")

    def connect_and_run(self):
        attempts = 0
        while attempts < self.max_reconnect_attempts:
            try:
                if self.app_state.emulator_name:
                    emulator_name = self.app_state.emulator_name
                else:
                    emulator_name = self.get_emulator_name()

                if not emulator_name:
                    self.log_callback("No emulator found, retrying...")
                    attempts += 1
                    time.sleep(self.reconnect_delay)
                    continue

                # Try to connect
                result = subprocess.run(
                    ["adb", "connect", emulator_name],
                    timeout=10,
                    capture_output=True,
                    text=True,
                )

                if "connected" in result.stdout.lower():
                    if self.wait_for_device():
                        self.log_callback(f"Successfully connected to {emulator_name}")
                        return True
                    else:
                        self.log_callback("Device connection timed out")
                else:
                    self.log_callback(f"Failed to connect: {result.stdout}")

            except Exception as e:
                self.log_callback(f"Connection attempt {attempts + 1} failed: {e}")

            attempts += 1
            time.sleep(self.reconnect_delay)

        self.log_callback("Failed to connect after maximum attempts")
        return False

    def restart_emulator(self):
        self.log_callback("Initiating emulator restart sequence...")
        try:
            # First try graceful shutdown
            subprocess.run(["adb", "shell", "reboot"], timeout=10)
            time.sleep(5)

            # Kill any existing emulator processes
            if os.name == "nt":  # Windows
                subprocess.run(
                    ["taskkill", "/F", "/IM", "dnplayer.exe"], capture_output=True
                )
            else:  # Linux/Mac
                subprocess.run(["pkill", "dnplayer"], capture_output=True)

            time.sleep(5)

            # Start emulator
            emulator_path = self.app_state.program_path
            if not emulator_path:
                self.log_callback("Error: Emulator path not set")
                return False

            exe_path = os.path.join(emulator_path, "dnplayer.exe")
            if not os.path.exists(exe_path):
                self.log_callback(f"Error: Emulator executable not found at {exe_path}")
                return False

            # Start the emulator process
            subprocess.Popen([exe_path])
            self.log_callback("Waiting for emulator to start...")

            # Wait for device to become available
            if self.wait_for_device(timeout=120):  # 2 minutes timeout
                self.log_callback("Emulator restarted successfully")
                return True
            else:
                self.log_callback("Emulator failed to start properly")
                return False

        except Exception as e:
            self.log_callback(f"Error during emulator restart: {e}")
            return False

    def get_all_devices(self):
        """Get list of all connected devices with their states"""
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                timeout=10,
                capture_output=True,
                text=True,
            )

            devices = []
            lines = result.stdout.splitlines()[1:]  # Skip header

            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        state = parts[1]
                        device_type = "unknown"

                        # Try to determine device type
                        if "model:" in line:
                            device_type = "phone"
                        elif "emulator" in line.lower():
                            device_type = "emulator"

                        devices.append(
                            {
                                "id": device_id,
                                "state": state,
                                "type": device_type,
                                "details": line,
                            }
                        )

            return devices

        except Exception as e:
            self.log_callback(f"Error getting devices: {e}")
            return []

    def connect_to_device(self, device_id):
        """Connect to a specific device by ID or IP:port"""
        try:
            # Kill ADB server first to reset connections
            subprocess.run(["adb", "kill-server"], timeout=5)
            time.sleep(2)

            # Start ADB server
            subprocess.run(["adb", "start-server"], timeout=5)
            time.sleep(2)

            # Try to connect
            result = subprocess.run(
                ["adb", "connect", device_id],
                timeout=10,
                capture_output=True,
                text=True,
            )

            if "connected" in result.stdout.lower():
                self.log_callback(f"Successfully connected to {device_id}")
                self.app_state.emulator_name = device_id
                return True
            else:
                self.log_callback(f"Failed to connect to {device_id}: {result.stdout}")
                return False

        except Exception as e:
            self.log_callback(f"Error connecting to device: {e}")
            return False

    def disconnect_all_devices(self):
        """Disconnect all connected devices"""
        try:
            subprocess.run(["adb", "disconnect"], timeout=5)
            self.log_callback("Disconnected all devices")
        except Exception as e:
            self.log_callback(f"Error disconnecting devices: {e}")
