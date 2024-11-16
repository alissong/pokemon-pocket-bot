import tkinter as tk


class MenuBuilder:
    def __init__(self, bot_ui):
        self.bot_ui = bot_ui
        self.root = bot_ui.root

    def build(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Configuration menu
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuration", menu=config_menu)
        config_menu.add_command(
            label="Select Emulator Path",
            command=self.bot_ui.ui_actions.select_emulator_path,
        )

        # Device menu
        device_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Devices", menu=device_menu)
        device_menu.add_command(
            label="Connect to Device",
            command=self.bot_ui.ui_actions.show_device_connection_dialog,
        )
        device_menu.add_command(
            label="Refresh Devices", command=self.bot_ui.ui_actions.refresh_devices
        )
        device_menu.add_separator()
        device_menu.add_command(
            label="Disconnect All",
            command=self.bot_ui.ui_actions.disconnect_all_devices,
        )

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(
            label="Take Screenshot", command=self.bot_ui.ui_actions.take_screenshot
        )
        tools_menu.add_command(
            label="Capture Region",
            command=self.bot_ui.ui_actions.take_region_screenshot,
        )
        tools_menu.add_command(
            label="Debug Window", command=self.bot_ui.ui_actions.toggle_debug_window
        )
