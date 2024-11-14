import os
from tkinter import filedialog

import cv2

from utils.adb_utils import take_screenshot
from views.dialogs.device_connection_dialog import DeviceConnectionDialog
from views.region_capture import RegionCaptureUI
from views.themes import UI_COLORS


class UIActions:
    def __init__(self, bot_ui):
        self.bot_ui = bot_ui

    def toggle_bot(self):
        if not self.bot_ui.bot_running:
            self.bot_ui.bot_running = True
            self.bot_ui.control_section.start_stop_button.config(
                text="Stop Bot", bg=UI_COLORS["error"]
            )
            self.bot_ui.status_section.status_label.config(
                text="Status: Running", fg=UI_COLORS["success"]
            )
            self.bot_ui.log_section.log_message("Bot started.")
            self.bot_ui.bot.start()
        else:
            self.bot_ui.bot.stop()
            self.bot_ui.bot_running = False
            self.bot_ui.control_section.start_stop_button.config(
                text="Start Bot", bg=UI_COLORS["info"]
            )
            self.bot_ui.status_section.status_label.config(
                text="Status: Not running", fg=UI_COLORS["error"]
            )
            self.bot_ui.log_section.log_message("Bot stopped.")

    def select_emulator_path(self):
        path = filedialog.askdirectory()
        if path:
            self.bot_ui.config_manager.save("path", path)
            self.bot_ui.app_state.program_path = path
            self.bot_ui.status_section.update_emulator_path(path)
            self.bot_ui.log_section.log_message("Emulator path selected and saved.")

    def take_screenshot(self):
        screenshot = take_screenshot()
        if screenshot is not None:
            self.bot_ui.log_section.log_message("Screenshot taken.")
        else:
            self.bot_ui.log_section.log_message("Failed to take screenshot.")

    def take_region_screenshot(self):
        screenshot = take_screenshot()
        if screenshot is not None:
            capture_ui = RegionCaptureUI(screenshot)
            region = capture_ui.get_region()

            if region:
                region_screenshot = self.bot_ui.bot.image_processor.capture_region(
                    region
                )
                images_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(images_dir, exist_ok=True)

                file_path = filedialog.asksaveasfilename(
                    initialdir=images_dir,
                    defaultextension=".PNG",
                    filetypes=[
                        ("PNG files", "*.png"),
                        ("JPEG files", "*.jpg"),
                        ("All files", "*.*"),
                    ],
                    title="Save Region Screenshot",
                )

                if file_path:
                    cv2.imwrite(file_path, region_screenshot)
                    self.bot_ui.log_section.log_message(
                        f"Region screenshot saved to: {file_path}"
                    )
                else:
                    self.bot_ui.log_section.log_message(
                        "Region screenshot capture cancelled."
                    )
            else:
                self.bot_ui.log_section.log_message(
                    "No region selected for screenshot."
                )
        else:
            self.bot_ui.log_section.log_message("Failed to take screenshot.")

    def show_device_connection_dialog(self):
        DeviceConnectionDialog(
            self.bot_ui.root,
            self.bot_ui.bot.emulator_controller,
            self.bot_ui.app_state,
            self.bot_ui.log_section.log_message,
        )

    def refresh_devices(self):
        devices = self.bot_ui.bot.emulator_controller.get_all_devices()
        self.bot_ui.log_section.log_message("Available devices:")
        for device in devices:
            self.bot_ui.log_section.log_message(f"• {device['id']} - {device['state']}")

    def disconnect_all_devices(self):
        self.bot_ui.bot.emulator_controller.disconnect_all_devices()
        self.bot_ui.log_section.log_message("Disconnected all devices")

    def on_closing(self):
        if self.bot_ui.bot_running:
            self.bot_ui.bot.stop()
            self.bot_ui.bot_running = False
        if self.bot_ui.card_name_event:
            self.bot_ui.card_name_event.set()
        self.bot_ui.root.destroy()

    def toggle_debug_window(self):
        if (
            self.bot_ui.debug_window.window is None
            or not self.bot_ui.debug_window.window.winfo_viewable()
        ):
            # Get main window's position and size
            main_x = self.bot_ui.root.winfo_x()
            main_y = self.bot_ui.root.winfo_y()
            main_height = self.bot_ui.root.winfo_height()
            self.bot_ui.debug_window.open_window(main_x, main_y, main_height)
        else:
            self.bot_ui.debug_window.close_window()
