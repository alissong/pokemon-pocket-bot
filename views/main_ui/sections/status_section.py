import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import UI_COLORS, UI_FONTS


class StatusSection:
    def __init__(self, parent, bot_ui):
        self.bot_ui = bot_ui
        self.section = SectionFrame(parent, "Status")
        self.section.frame.pack(fill=tk.X, pady=5)
        self.setup_status()

    def setup_status(self):
        status_container = tk.Frame(self.section.frame, bg=UI_COLORS["bg"])
        status_container.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(
            status_container,
            text="Status: Not running",
            font=UI_FONTS["text"],
            fg=UI_COLORS["error"],
            bg=UI_COLORS["bg"],
        )
        self.status_label.pack(side=tk.LEFT, pady=5)

        debug_button = tk.Button(
            status_container,
            text="🔍 Debug",
            command=self.bot_ui.ui_actions.toggle_debug_window,
            font=UI_FONTS["text"],
            relief=tk.FLAT,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            padx=10,
        )
        debug_button.pack(side=tk.RIGHT, padx=5)

        self.selected_emulator_label = tk.Label(
            self.section.frame,
            text="",
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["entry_fg"],
            relief=tk.FLAT,
            padx=5,
        )
        self.selected_emulator_label.pack(fill=tk.X, padx=5, pady=2)

    def update_emulator_path(self, path):
        self.selected_emulator_label.config(text=path)
