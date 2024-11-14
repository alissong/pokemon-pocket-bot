# src/views/components/collapsible_section.py

import tkinter as tk

from views.base.base_component import BaseComponent
from views.themes import UI_COLORS, UI_FONTS


class CollapsibleSection(BaseComponent):
    def __init__(self, parent, title):
        super().__init__(parent, UI_COLORS["bg"])
        self.title = title
        self.is_collapsed = False
        self.setup()

    def setup(self):
        self.header = tk.Frame(self.frame, bg=self.bg_color)
        self.header.pack(fill=tk.X)

        self.toggle_button = tk.Button(
            self.header,
            text="▼",
            command=self.toggle,
            font=("Helvetica", 8),
            width=2,
            height=1,
            relief=tk.FLAT,
            bg=self.bg_color,
            fg=UI_COLORS["fg"],
        )
        self.toggle_button.pack(side=tk.RIGHT, padx=2, pady=0)

        self.label = tk.Label(
            self.header,
            text=self.title,
            font=UI_FONTS["header"],
            bg=self.bg_color,
            fg=UI_COLORS["accent"],
        )
        self.label.pack(side=tk.LEFT, pady=5)

        self.content = tk.Frame(self.frame, bg=self.bg_color)
        self.content.pack(fill=tk.BOTH, expand=True)

    def toggle(self):
        if self.is_collapsed:
            self.content.pack(fill=tk.BOTH, expand=True)
            self.toggle_button.config(text="▼")
            self.is_collapsed = False
        else:
            self.content.pack_forget()
            self.toggle_button.config(text="▲")
            self.is_collapsed = True
