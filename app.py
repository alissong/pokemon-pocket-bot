import tkinter as tk

from models.app_state import AppState
from views.main_ui.bot_ui import BotUI

if __name__ == "__main__":
    root = tk.Tk()
    app_state = AppState()
    ui = BotUI(root, app_state)
    root.mainloop()
