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
                self.log_callback("⏳ Waiting for device...")
            except Exception as e:
                self.log_callback(f"❌ Device error: {e}")

            time.sleep(2)

        return False

    def get_emulator_name(self):
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
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
                        # Only add online devices
                        if state == "device":
                            devices.append(device_id)

            if not devices:
                self.log_callback("No online devices found")
                return None

            if len(devices) > 1:
                # Multiple devices found - let UI handle selection
                return None

            # Single device found - return it
            return devices[0]

        except Exception as e:
            self.log_callback(f"Error getting emulator name: {e}")
            return None

    def handle_offline_devices(self, device_ids):
        """Handle offline devices by killing ADB server and reconnecting"""
        self.log_callback("🔄 Recovering offline devices...")
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
            self.log_callback(f"❌ Recovery failed: {e}")

    def connect_to_device(self, device_id):
        """Connect to a specific device by ID or IP:port"""
        try:
            # Check if device is already connected
            devices = self.get_all_devices()
            for device in devices:
                if device["id"] == device_id and device["state"] == "device":
                    self.log_callback(f"Device {device_id} is already connected")
                    self.app_state.emulator_name = device_id
                    return True

            # If not connected, try to connect
            self.log_callback(f"Attempting to connect to {device_id}...")

            # For emulator connections, modify the address format
            if device_id.startswith("emulator-"):
                connect_address = f"127.0.0.1:{device_id.split('-')[1]}"
            else:
                connect_address = device_id

            result = subprocess.run(
                ["adb", "connect", connect_address],
                timeout=10,
                capture_output=True,
                text=True,
            )

            if "connected" in result.stdout.lower():
                if self.wait_for_device():
                    self.log_callback(f"Successfully connected to {device_id}")
                    self.app_state.emulator_name = device_id
                    return True
                else:
                    self.log_callback("Device connection timed out")
                    return False
            else:
                self.log_callback(f"Failed to connect to {device_id}: {result.stdout}")
                return False

        except Exception as e:
            self.log_callback(f"Error connecting to device: {e}")
            return False

    def connect_and_run(self):
        """Initial connection attempt when bot starts"""
        attempts = 0
        while attempts < self.max_reconnect_attempts:
            try:
                # Get all available devices
                devices = self.get_all_devices()

                if not devices:
                    self.log_callback("No devices found")
                    return False

                # If we have a stored device name, try to connect to it first
                if self.app_state.emulator_name:
                    for device in devices:
                        if device["id"] == self.app_state.emulator_name:
                            if self.connect_to_device(device["id"]):
                                return True
                            break

                # If no stored device or connection failed, try first available device
                for device in devices:
                    if device["state"] == "device":
                        if self.connect_to_device(device["id"]):
                            return True
                        break

                self.log_callback("No available devices to connect to")

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

    def disconnect_all_devices(self):
        """Disconnect all connected devices"""
        try:
            subprocess.run(["adb", "disconnect"], timeout=5)
            self.log_callback("Disconnected all devices")
        except Exception as e:
            self.log_callback(f"Error disconnecting devices: {e}")
