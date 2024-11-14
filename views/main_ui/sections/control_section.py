import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import UI_COLORS, UI_FONTS


class ControlSection:
    def __init__(self, parent, bot_ui):
        self.bot_ui = bot_ui
        self.section = SectionFrame(parent, "Bot Controls")
        self.section.frame.pack(fill=tk.X, pady=5)
        self.setup_controls()

    def setup_controls(self):
        button_style = {
            "font": UI_FONTS["text"],
            "relief": tk.FLAT,
            "bg": UI_COLORS["button_bg"],
            "fg": UI_COLORS["fg"],
            "padx": 15,
            "pady": 5,
        }

        self.start_stop_button = tk.Button(
            self.section.frame,
            text="Start Bot",
            command=self.bot_ui.ui_actions.toggle_bot,
            **button_style,
        )
        self.start_stop_button.pack(pady=5)
