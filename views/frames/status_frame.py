import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import UI_COLORS, UI_FONTS


class StatusFrame:
    def __init__(self, parent, controller):
        self.controller = controller
        self.frame = SectionFrame(parent, "Status").frame
        self.setup_status()

    def setup_status(self):
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]
        button_bg_color = UI_COLORS["button_bg"]
        entry_bg_color = UI_COLORS["entry_bg"]
        entry_fg_color = UI_COLORS["entry_fg"]
        text_font = UI_FONTS["text"]

        # Create a container for status and debug button
        status_container = tk.Frame(self.frame, bg=bg_color)
        status_container.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(
            status_container,
            text="Status: Not running",
            font=text_font,
            fg=UI_COLORS["error"],
            bg=bg_color,
        )
        self.status_label.pack(side=tk.LEFT, pady=5)

        # Add debug button
        debug_button = tk.Button(
            status_container,
            text="🔍 Debug",
            command=self.controller.toggle_debug_window,
            font=text_font,
            relief=tk.FLAT,
            bg=button_bg_color,
            fg=fg_color,
            padx=10,
        )
        debug_button.pack(side=tk.RIGHT, padx=5)

        # Selected emulator path display
        self.selected_emulator_label = tk.Label(
            self.frame,
            text="",
            font=text_font,
            bg=entry_bg_color,
            fg=entry_fg_color,
            relief=tk.FLAT,
            padx=5,
        )
        self.selected_emulator_label.pack(fill=tk.X, padx=5, pady=2)

    def update_status(self, status_text, success=True):
        self.status_label.config(
            text=f"Status: {status_text}",
            fg=UI_COLORS["success"] if success else UI_COLORS["error"],
        )

    def update_emulator_path(self, path):
        self.selected_emulator_label.config(text=path)
