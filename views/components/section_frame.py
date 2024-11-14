# views/components/section_frame.py
import tkinter as tk

from views.themes import UI_COLORS, UI_FONTS


class SectionFrame:
    def __init__(self, parent, title):
        self.parent = parent
        self.title = title
        self.frame = self.create_section()

    def create_section(self):
        section = tk.Frame(self.parent, bg=UI_COLORS["bg"], bd=2, relief=tk.GROOVE)
        section.pack(fill=tk.X, pady=5)

        header = tk.Label(
            section,
            text=self.title,
            font=UI_FONTS["header"],
            bg=UI_COLORS["bg"],
            fg=UI_COLORS["accent"],
        )
        header.pack(fill=tk.X, padx=5, pady=2)

        content = tk.Frame(section, bg=UI_COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return content
