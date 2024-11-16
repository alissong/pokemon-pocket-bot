import tkinter as tk

from views.base.base_dialog import BaseDialog
from views.themes import UI_COLORS, UI_FONTS


class DeviceConnectionDialog(BaseDialog):
    def __init__(self, parent, emulator_controller, app_state, log_callback):
        self.emulator_controller = emulator_controller
        self.app_state = app_state
        self.log_callback = log_callback
        super().__init__(parent, "Device Connection Manager", "500x500")

    def setup(self):
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]
        button_bg_color = UI_COLORS["button_bg"]
        section_font = UI_FONTS["text"]

        # Connection Status Frame
        status_frame = tk.LabelFrame(
            self.window,
            text="Connection Status",
            font=section_font,
            bg=bg_color,
            fg=fg_color,
        )
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.current_device_label = tk.Label(
            status_frame,
            text=f"Current device: {self.app_state.emulator_name or 'None'}",
            font=section_font,
            bg=bg_color,
            fg=fg_color,
        )
        self.current_device_label.pack(pady=5)

        self.connection_status_label = tk.Label(
            status_frame,
            text="Status: Not connected",
            font=section_font,
            fg=UI_COLORS["warning"],
            bg=bg_color,
        )
        self.connection_status_label.pack(pady=5)

        # Available Devices Frame
        device_frame = tk.LabelFrame(
            self.window,
            text="Available Devices",
            font=section_font,
            bg=bg_color,
            fg=fg_color,
        )
        device_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.devices_list = tk.Listbox(
            device_frame, font=section_font, selectmode=tk.SINGLE
        )
        self.devices_list.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5
        )

        scrollbar = tk.Scrollbar(device_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.devices_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.devices_list.yview)

        # Buttons Frame
        buttons_frame = tk.Frame(self.window, bg=bg_color)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        refresh_btn = tk.Button(
            buttons_frame,
            text="🔄 Refresh",
            command=self.refresh_device_list,
            bg=button_bg_color,
            fg=fg_color,
            width=12,
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        connect_btn = tk.Button(
            buttons_frame,
            text="🔌 Connect",
            command=self.connect_selected,
            bg=button_bg_color,
            fg=fg_color,
            width=12,
        )
        connect_btn.pack(side=tk.LEFT, padx=5)

        disconnect_btn = tk.Button(
            buttons_frame,
            text="⚡ Disconnect",
            command=self.disconnect_current,
            bg=button_bg_color,
            fg=fg_color,
            width=12,
        )
        disconnect_btn.pack(side=tk.LEFT, padx=5)

        close_btn = tk.Button(
            buttons_frame,
            text="✖ Close",
            command=self.destroy,
            bg=button_bg_color,
            fg=fg_color,
            width=12,
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

        # Manual Connection Frame
        manual_frame = tk.LabelFrame(
            self.window,
            text="Manual Connection",
            font=section_font,
            bg=bg_color,
            fg=fg_color,
        )
        manual_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            manual_frame, text="IP:Port", font=section_font, bg=bg_color, fg=fg_color
        ).pack(side=tk.LEFT, padx=5)

        self.ip_entry = tk.Entry(manual_frame, font=section_font)
        self.ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        manual_connect_btn = tk.Button(
            manual_frame,
            text="Connect",
            command=self.connect_manual,
            bg=button_bg_color,
            fg=fg_color,
        )
        manual_connect_btn.pack(side=tk.RIGHT, padx=5)

        # Initial Population of Devices
        self.refresh_device_list()

    def refresh_device_list(self):
        self.devices_list.delete(0, tk.END)
        devices = self.emulator_controller.get_all_devices()

        if not devices:
            self.connection_status_label.config(
                text="Status: No devices found", fg=UI_COLORS["error"]
            )
            return

        for device in devices:
            state_text = (
                "✓ Available" if device["state"] == "device" else "✗ Unavailable"
            )
            is_current = (
                " (Current)" if device["id"] == self.app_state.emulator_name else ""
            )
            self.devices_list.insert(
                tk.END, f"{device['id']} - {state_text}{is_current}"
            )

            if (
                device["id"] == self.app_state.emulator_name
                and device["state"] == "device"
            ):
                self.connection_status_label.config(
                    text=f"Status: Connected to {device['id']}",
                    fg=UI_COLORS["success"],
                )
            elif device["state"] == "device":
                self.connection_status_label.config(
                    text="Status: Device available", fg=UI_COLORS["info"]
                )

    def connect_selected(self):
        selection = self.devices_list.curselection()
        if not selection:
            self.connection_status_label.config(
                text="Status: Please select a device", fg=UI_COLORS["warning"]
            )
            return

        device_str = self.devices_list.get(selection[0])
        device_id = device_str.split(" - ")[0].strip()

        self.connection_status_label.config(
            text=f"Status: Connecting to {device_id}...", fg=UI_COLORS["info"]
        )
        self.window.update()

        if self.emulator_controller.connect_to_device(device_id):
            self.connection_status_label.config(
                text=f"Status: Connected to {device_id}", fg=UI_COLORS["success"]
            )
            self.app_state.emulator_name = device_id
            self.current_device_label.config(text=f"Current device: {device_id}")
            self.refresh_device_list()
            self.log_callback(f"Connected to device: {device_id}")
        else:
            self.connection_status_label.config(
                text="Status: Connection failed", fg=UI_COLORS["error"]
            )
            self.log_callback(f"Failed to connect to device: {device_id}")

    def disconnect_current(self):
        if not self.app_state.emulator_name:
            self.connection_status_label.config(
                text="Status: No device connected", fg=UI_COLORS["warning"]
            )
            return

        self.emulator_controller.disconnect_all_devices()
        self.app_state.emulator_name = None
        self.current_device_label.config(text="Current device: None")
        self.connection_status_label.config(
            text="Status: Disconnected", fg=UI_COLORS["info"]
        )
        self.refresh_device_list()
        self.log_callback("Disconnected all devices.")

    def connect_manual(self):
        ip_port = self.ip_entry.get().strip()
        if not ip_port:
            self.connection_status_label.config(
                text="Status: Please enter IP:Port", fg=UI_COLORS["warning"]
            )
            return

        if self.emulator_controller.connect_to_device(ip_port):
            self.connection_status_label.config(
                text=f"Status: Connected to {ip_port}", fg=UI_COLORS["success"]
            )
            self.app_state.emulator_name = ip_port
            self.current_device_label.config(text=f"Current device: {ip_port}")
            self.refresh_device_list()
            self.log_callback(f"Connected to device: {ip_port}")
        else:
            self.connection_status_label.config(
                text="Status: Connection failed", fg=UI_COLORS["error"]
            )
            self.log_callback(f"Failed to connect to device: {ip_port}")
