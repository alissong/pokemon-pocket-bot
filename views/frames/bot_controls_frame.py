import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import UI_COLORS, UI_FONTS


class BotControlsFrame:
    def __init__(self, parent, controller):
        self.controller = controller
        self.frame = SectionFrame(parent, "Bot Controls").frame
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
            self.frame,
            text="Start Bot",
            command=self.controller.toggle_bot,
            **button_style,
        )
        self.start_stop_button.pack(pady=5)

    def start_bot(self):
        self.start_stop_button.config(text="Stop Bot", bg=UI_COLORS["error"])

    def stop_bot(self):
        self.start_stop_button.config(text="Start Bot", bg=UI_COLORS["info"])
