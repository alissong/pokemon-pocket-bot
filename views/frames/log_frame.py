import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import GAME_STATE_CONFIG, UI_COLORS, UI_FONTS


class LogFrame:
    def __init__(self, parent, controller):
        self.controller = controller
        self.frame = SectionFrame(parent, "Log").frame
        self.setup_log()

    def setup_log(self):
        bg_color = UI_COLORS["bg"]
        # entry_bg_color = UI_COLORS["entry_bg"]
        # entry_fg_color = UI_COLORS["entry_fg"]
        # text_font = UI_FONTS["text"]

        # Create log text with scrollbar
        log_container = tk.Frame(self.frame, bg=bg_color)
        log_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(
            log_container, bg=bg_color, troughcolor=UI_COLORS["entry_bg"]
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_container,
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["entry_fg"],
            width=GAME_STATE_CONFIG["text_width"]["log"],
            height=40,
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set, state=tk.DISABLED)

    def append_log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
