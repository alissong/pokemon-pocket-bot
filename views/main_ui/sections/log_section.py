import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import GAME_STATE_CONFIG, UI_COLORS, UI_FONTS


class LogSection:
    def __init__(self, parent, bot_ui):
        self.bot_ui = bot_ui
        self.section = SectionFrame(parent, "Log")
        self.section.frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.setup_log()

    def setup_log(self):
        # Create log text with scrollbar
        log_container = tk.Frame(self.section.frame, bg=UI_COLORS["bg"])
        log_container.pack(fill=tk.BOTH, expand=True)

        # Create a frame for buttons
        button_frame = tk.Frame(log_container, bg=UI_COLORS["bg"])
        button_frame.pack(fill=tk.X, pady=(0, 5))

        # Add clear button
        clear_button = tk.Button(
            button_frame,
            text="Clear Log",
            command=self.clear_log,
            font=UI_FONTS["text"],
            relief=tk.FLAT,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            padx=10,
        )
        clear_button.pack(side=tk.RIGHT, padx=5)

        # Create text widget and scrollbar
        scrollbar = tk.Scrollbar(
            log_container, bg=UI_COLORS["bg"], troughcolor=UI_COLORS["entry_bg"]
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

        # Configure scrollbar
        scrollbar.config(command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def clear_log(self):
        """Clear the log text widget"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_message("Log cleared.")

    def log_message(self, message):
        """Thread-safe logging method"""
        if not self.bot_ui.root.winfo_exists() or not self.bot_ui.bot_running:
            return

        def _log():
            if not self.bot_ui.root.winfo_exists() or not self.bot_ui.bot_running:
                return

            # Check if scrollbar is at the bottom before inserting text
            was_at_bottom = self.log_text.yview()[1] == 1.0

            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")

            # Only auto-scroll if we were already at the bottom
            if was_at_bottom:
                self.log_text.see(tk.END)

            self.log_text.config(state=tk.DISABLED)

        # Schedule the log update on the main thread
        self.bot_ui.root.after(0, _log)
