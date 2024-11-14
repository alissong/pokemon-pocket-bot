import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk

from views.base.base_dialog import BaseDialog
from views.themes import UI_COLORS, UI_FONTS


class CardOptionsDialog(BaseDialog):
    def __init__(
        self,
        parent,
        similarities,
        zoomed_card_image,
        select_callback,
        max_zoomed_height=200,
        window_size="700x700",
        columns=3,
        card_dimensions=(150, 210),
    ):
        self.similarities = similarities
        self.zoomed_card_image = zoomed_card_image
        self.select_callback = select_callback
        self.max_zoomed_height = max_zoomed_height
        self.window_size = window_size
        self.columns = columns
        self.card_dimensions = card_dimensions
        super().__init__(parent, "Select the Correct Card", self.window_size)

    def setup(self):
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]
        accent_color = UI_COLORS["accent"]

        # Main Container
        main_frame = tk.Frame(self.window, bg=bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top Section with Zoomed Card
        top_frame = tk.Frame(main_frame, bg=bg_color)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            top_frame,
            text="Your Card:",
            font=("Helvetica", 14, "bold"),
            bg=bg_color,
            fg=accent_color,
        ).pack(pady=5)

        cv_image = cv2.cvtColor(self.zoomed_card_image, cv2.COLOR_BGR2RGB)
        height, width = cv_image.shape[:2]
        if height > self.max_zoomed_height:
            scale = self.max_zoomed_height / height
            new_width = int(width * scale)
            cv_image = cv2.resize(cv_image, (new_width, self.max_zoomed_height))

        pil_image = Image.fromarray(cv_image)
        tk_image = ImageTk.PhotoImage(pil_image)

        self.zoomed_label = tk.Label(top_frame, image=tk_image, bg=bg_color)
        self.zoomed_label.image = tk_image  # Keep a reference
        self.zoomed_label.pack()

        # Scrollable Frame for Card Options
        canvas = tk.Canvas(main_frame, bg=bg_color)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.options_frame = tk.Frame(canvas, bg=bg_color)

        self.options_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.options_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Populate Card Options
        self.card_images = []  # To keep references

        for idx, (card, similarity) in enumerate(self.similarities):
            row = idx // self.columns
            col = idx % self.columns

            card_frame = tk.Frame(
                self.options_frame, relief=tk.RIDGE, borderwidth=2, bg=bg_color
            )
            card_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            try:
                api_card_image = card["image"]
                api_card_image = cv2.resize(api_card_image, self.card_dimensions)
                api_cv_image = cv2.cvtColor(api_card_image, cv2.COLOR_BGR2RGB)
                api_pil_image = Image.fromarray(api_cv_image)
                api_tk_image = ImageTk.PhotoImage(api_pil_image)
            except Exception as e:
                messagebox.showerror(
                    "Image Error",
                    f"Failed to load image for card: {card.get('name')}\n{e}",
                )
                self.select_callback(None)
                self.destroy()
                return

            card_label = tk.Label(card_frame, image=api_tk_image, bg=bg_color)
            card_label.image = api_tk_image  # Keep a reference
            card_label.pack(pady=5)

            info_text = f"Name: {card.get('name', 'Unknown')}\nSet: {card.get('set_name', 'Unknown')}\nSimilarity: {similarity:.2f}"
            info_label = tk.Label(
                card_frame,
                text=info_text,
                wraplength=self.card_dimensions[0],
                font=("Helvetica", 10),
                bg=bg_color,
                fg=fg_color,
            )
            info_label.pack(pady=2)

            select_button = tk.Button(
                card_frame,
                text="Select",
                command=lambda c=card: self.select_and_close(c),
                width=12,
                bg=UI_COLORS["button_bg"],
                fg=fg_color,
                font=UI_FONTS["text"],
            )
            select_button.pack(pady=5)

            self.card_images.append(api_tk_image)  # Keep reference

        # Configure grid columns
        for i in range(self.columns):
            self.options_frame.grid_columnconfigure(i, weight=1)

        # Bind mousewheel for scrolling
        self.window.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_mousewheel(self, event):
        self.options_frame.master.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def select_and_close(self, card):
        if card:
            self.select_callback(card)
            self.destroy()
        else:
            self.select_callback(None)
            self.destroy()
