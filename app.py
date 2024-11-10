import tkinter as tk

from app_state import AppState
from ui import BotUI

if __name__ == "__main__":
    root = tk.Tk()
    app_state = AppState()
    ui = BotUI(root, app_state)
    root.mainloop()
