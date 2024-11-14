import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk

from views.base.base_dialog import BaseDialog
from views.themes import UI_COLORS, UI_FONTS


class CardPromptDialog(BaseDialog):
    def __init__(
        self,
        parent,
        image,
        event,
        error_message=None,
        timeout=12,
        max_image_height=400,
        callback=None,
    ):
        self.image = image
        self.event = event
        self.error_message = error_message
        self.timeout = timeout
        self.max_image_height = max_image_height
        self.card_name = None
        self.callback = callback
        super().__init__(parent, "Unknown Card", "400x600")

    def setup(self):
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]

        # Timeout Label
        self.timeout_label = tk.Label(
            self.window,
            text=f"Time remaining: {self.timeout}s",
            fg=UI_COLORS["error"],
            bg=bg_color,
            font=UI_FONTS["text"],
        )
        self.timeout_label.pack(pady=5)

        # Start the countdown
        self.remaining_time = self.timeout
        self.update_timeout()

        # Display the image
        cv_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        height, width = cv_image.shape[:2]

        if height > self.max_image_height:
            scale = self.max_image_height / height
            new_width = int(width * scale)
            cv_image = cv2.resize(cv_image, (new_width, self.max_image_height))

        pil_image = Image.fromarray(cv_image)
        tk_image = ImageTk.PhotoImage(pil_image)

        self.image_label = tk.Label(self.window, image=tk_image, bg=bg_color)
        self.image_label.image = tk_image  # Keep a reference
        self.image_label.pack(padx=10, pady=10)

        # Error Message (if any)
        if self.error_message:
            self.error_label = tk.Label(
                self.window,
                text=self.error_message,
                fg="red",
                bg=bg_color,
                font=UI_FONTS["text"],
            )
            self.error_label.pack(pady=5)

        # Entry for Card Name
        tk.Label(
            self.window,
            text="Enter card name:",
            bg=bg_color,
            fg=fg_color,
            font=UI_FONTS["text"],
        ).pack(pady=5)

        self.entry = tk.Entry(self.window, font=UI_FONTS["text"])
        self.entry.pack(pady=5)
        self.entry.bind("<Return>", self.submit)

        # Buttons
        submit_btn = tk.Button(
            self.window,
            text="Submit",
            command=self.submit,
            bg=UI_COLORS["button_bg"],
            fg=fg_color,
            font=UI_FONTS["text"],
        )
        submit_btn.pack(pady=5)

        cancel_btn = tk.Button(
            self.window,
            text="Cancel",
            command=self.cancel,
            bg=UI_COLORS["button_bg"],
            fg=fg_color,
            font=UI_FONTS["text"],
        )
        cancel_btn.pack(pady=5)

        self.entry.focus_set()

    def update_timeout(self):
        if self.remaining_time > 0:
            self.timeout_label.config(text=f"Time remaining: {self.remaining_time}s")
            self.remaining_time -= 1
            self.window.after(1000, self.update_timeout)
        else:
            self.cancel()

    def submit(self, event=None):
        self.card_name = self.entry.get().strip()
        if self.card_name is not None:
            if self.callback:
                self.callback(self.card_name)
            self.event.set()
            self.destroy()
        else:
            messagebox.showwarning("Input Error", "Please enter a valid card name.")

    def cancel(self):
        self.card_name = None
        self.event.set()
        self.destroy()
