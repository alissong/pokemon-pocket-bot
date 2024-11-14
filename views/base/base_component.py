import tkinter as tk
from abc import ABC, abstractmethod


class BaseComponent(ABC):
    def __init__(self, parent, bg_color):
        self.parent = parent
        self.bg_color = bg_color
        self.frame = tk.Frame(self.parent, bg=self.bg_color)
        self.frame.pack(fill=tk.BOTH, expand=True)

    @abstractmethod
    def setup(self):
        pass
