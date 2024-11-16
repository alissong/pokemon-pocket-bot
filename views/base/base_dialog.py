import tkinter as tk
from abc import ABC, abstractmethod


class BaseDialog(ABC):
    def __init__(self, parent, title, size="400x300"):
        self.parent = parent
        self.window = tk.Toplevel(self.parent)
        self.window.title(title)
        self.window.geometry(size)
        self.window.transient(self.parent)
        self.window.grab_set()
        self.setup()

    @abstractmethod
    def setup(self):
        pass

    def destroy(self):
        self.window.destroy()
