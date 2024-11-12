# src/views/ui.py

import tkinter as tk
from tkinter import filedialog

import cv2
import numpy as np
import requests
from PIL import Image, ImageTk
from utils.adb_utils import take_screenshot
from utils.config_manager import ConfigManager

from bot import PokemonBot


class BotUI:
    def __init__(self, root, app_state):
        self.root = root
        self.app_state = app_state
        self.root.title("Pokemon Pocket Bot")
        self.config_manager = ConfigManager()
        self.bot = PokemonBot(app_state, self.log_message, self)

        self.bot_running = False

        self.card_name_event = None
        self.card_name = None
        self.selected_card = None

        self.setup_ui()
        self.load_configs()

    def setup_ui(self):
        self.root.geometry("450x650")
        tk.Label(
            self.root, text="Pokemon Pocket Bot ⚔️", font=("Helvetica", 16, "bold")
        ).pack(pady=10)

        select_path_frame = tk.Frame(self.root)
        select_path_frame.pack(pady=5)

        self.select_path_button = tk.Button(
            select_path_frame,
            text="Select Emulator Path",
            command=self.select_emulator_path,
            font=("Helvetica", 10),
        )
        self.select_path_button.pack(side=tk.LEFT, padx=5)

        self.selected_emulator_label = tk.Label(
            select_path_frame, text="", font=("Helvetica", 10)
        )
        self.selected_emulator_label.pack(side=tk.LEFT)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.start_stop_button = tk.Button(
            button_frame,
            text="Start Bot",
            command=self.toggle_bot,
            width=20,
            relief=tk.RAISED,
            bd=3,
            font=("Helvetica", 10),
        )
        self.start_stop_button.pack(side=tk.LEFT, padx=5)

        action_frame = tk.Frame(self.root)
        action_frame.pack(pady=10)

        self.screenshot_button = tk.Button(
            action_frame,
            text="Screenshot",
            command=self.take_screenshot,
            width=20,
            relief=tk.RAISED,
            bd=3,
            font=("Helvetica", 10),
        )
        self.screenshot_button.pack(side=tk.LEFT, padx=5)

        region_frame = tk.Frame(self.root)
        region_frame.pack(pady=10)

        tk.Label(region_frame, text="Start X:", font=("Helvetica", 10)).grid(
            row=0, column=0, padx=5
        )
        self.start_x_entry = tk.Entry(region_frame, width=15, font=("Helvetica", 10))
        self.start_x_entry.grid(row=0, column=1)

        tk.Label(region_frame, text="Start Y:", font=("Helvetica", 10)).grid(
            row=0, column=2, padx=5
        )
        self.start_y_entry = tk.Entry(region_frame, width=15, font=("Helvetica", 10))
        self.start_y_entry.grid(row=0, column=3)

        tk.Label(region_frame, text="Width:", font=("Helvetica", 10)).grid(
            row=1, column=0, padx=5
        )
        self.width_entry = tk.Entry(region_frame, width=15, font=("Helvetica", 10))
        self.width_entry.grid(row=1, column=1)

        tk.Label(region_frame, text="Height:", font=("Helvetica", 10)).grid(
            row=1, column=2, padx=5
        )
        self.height_entry = tk.Entry(region_frame, width=15, font=("Helvetica", 10))
        self.height_entry.grid(row=1, column=3)

        self.region_screenshot_button = tk.Button(
            region_frame,
            text="Capture Region",
            command=self.take_region_screenshot,
            width=20,
            relief=tk.RAISED,
            bd=3,
            font=("Helvetica", 10),
        )
        self.region_screenshot_button.grid(row=2, column=0, columnspan=4, pady=10)

        self.status_label = tk.Label(
            self.root, text="Status: Not running", font=("Helvetica", 10)
        )
        self.status_label.pack()

        self.log_text = tk.Text(self.root, font=("Helvetica", 10))
        self.log_text.pack()

    def load_configs(self):
        config = self.config_manager.load()
        if config:
            self.app_state.update(config)
            self.selected_emulator_label.config(text=self.app_state.program_path)

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def toggle_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.start_stop_button.config(text="Stop Bot")
            self.status_label.config(text="Status: Running")
            self.log_message("Bot started.")

            self.bot.start()
        else:
            self.bot.stop()
            self.bot_running = False
            self.start_stop_button.config(text="Start Bot")
            self.status_label.config(text="Status: Not running")
            self.log_message("Bot stopped.")

    def select_emulator_path(self):
        emulator_path = filedialog.askdirectory()
        if emulator_path:
            self.config_manager.save("path", emulator_path)
            self.app_state.program_path = emulator_path
            self.selected_emulator_label.config(text=emulator_path)
            self.log_message("Emulator path selected and saved.")

    def take_screenshot(self):
        screenshot = take_screenshot()
        self.log_message("Screenshot taken.")

    def take_region_screenshot(self):
        self.log_message(self.start_x_entry.get())

        if (
            self.start_x_entry.get()
            and self.start_y_entry.get()
            and self.width_entry.get()
            and self.height_entry.get()
        ):
            region = (
                int(self.start_x_entry.get()),
                int(self.start_y_entry.get()),
                int(self.width_entry.get()),
                int(self.height_entry.get()),
            )
            screenshot = self.bot.image_processor.capture_region(region)
            self.log_message("Region screenshot taken.")

    def request_card_name(self, image, event, error_message=None):
        self.card_name_event = event
        self.card_name = None  # Reset card_name
        self.root.after(0, self.show_card_prompt, image, error_message)

    def show_card_prompt(self, image, error_message=None):
        window = tk.Toplevel(self.root)
        window.title("Unknown Card")
        window.geometry("400x600")

        # Add timeout label
        timeout_label = tk.Label(window, text="Time remaining: 30s", fg="red")
        timeout_label.pack(pady=5)

        # Timeout counter
        remaining_time = 30

        def update_timeout():
            nonlocal remaining_time
            if remaining_time > 0 and window.winfo_exists():
                remaining_time -= 1
                timeout_label.config(text=f"Time remaining: {remaining_time}s")
                window.after(1000, update_timeout)
            elif remaining_time <= 0 and window.winfo_exists():
                cancel()

        window.after(1000, update_timeout)

        # Convert and resize image
        cv_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = cv_image.shape[:2]
        max_height = 400

        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            cv_image = cv2.resize(cv_image, (new_width, max_height))

        pil_image = Image.fromarray(cv_image)
        tk_image = ImageTk.PhotoImage(pil_image)

        label = tk.Label(window, image=tk_image)
        label.image = tk_image
        label.pack(padx=10, pady=10)

        if error_message:
            error_label = tk.Label(window, text=error_message, fg="red")
            error_label.pack(pady=5)

        tk.Label(window, text="Enter card name:").pack(pady=5)

        def submit():
            self.card_name = entry.get()
            self.card_name_event.set()
            window.destroy()

        def on_enter(event):
            submit()

        entry = tk.Entry(window)
        entry.pack(pady=5)
        entry.bind("<Return>", on_enter)  # Bind Enter key to submit

        def cancel():
            self.card_name = None
            self.card_name_event.set()
            window.destroy()

        tk.Button(window, text="Submit", command=submit).pack(pady=5)
        tk.Button(window, text="Cancel", command=cancel).pack(pady=5)
        entry.focus_set()

    def show_card_options(self, similarities, zoomed_card_image, event):
        window = tk.Toplevel(self.root)
        window.title("Select the Correct Card")
        window.geometry("800x600")

        # Create main container with fixed height
        main_frame = tk.Frame(window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top section with zoomed card
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(top_frame, text="Your Card:", font=("Helvetica", 14, "bold")).pack(
            pady=5
        )

        # Scale zoomed card image
        cv_image = cv2.cvtColor(zoomed_card_image, cv2.COLOR_BGR2RGB)
        height, width = cv_image.shape[:2]
        max_height = 200
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            cv_image = cv2.resize(cv_image, (new_width, max_height))

        pil_image = Image.fromarray(cv_image)
        tk_image = ImageTk.PhotoImage(pil_image)
        label_image = tk.Label(top_frame, image=tk_image)
        label_image.image = tk_image
        label_image.pack()

        # Create scrollable frame for card options
        canvas = tk.Canvas(main_frame)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)

        # Create frame inside canvas for content
        content_frame = tk.Frame(canvas)
        content_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Add content frame to canvas
        canvas_frame = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Grid for cards (3 columns)
        COLUMNS = 3
        card_images = []  # Keep references to images

        for idx, (card, similarity) in enumerate(similarities):
            row = idx // COLUMNS
            col = idx % COLUMNS

            card_frame = tk.Frame(content_frame, relief=tk.RIDGE, borderwidth=2)
            card_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # Get and scale card image
            image_url = self.bot.card_data_service.get_card_image_url(card["id"])
            response = requests.get(image_url)
            image_data = np.asarray(bytearray(response.content), dtype=np.uint8)
            api_card_image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

            # Fixed size for all card images
            api_card_image = cv2.resize(api_card_image, (150, 210))
            api_cv_image = cv2.cvtColor(api_card_image, cv2.COLOR_BGR2RGB)
            api_pil_image = Image.fromarray(api_cv_image)
            api_tk_image = ImageTk.PhotoImage(api_pil_image)

            card_label = tk.Label(card_frame, image=api_tk_image)
            card_label.image = api_tk_image
            card_label.pack(pady=5)
            card_images.append(api_tk_image)

            info_text = f"Name: {card['name']}\nSet: {card['set_name']}\nSimilarity: {similarity:.2f}"
            info_label = tk.Label(
                card_frame, text=info_text, wraplength=150, font=("Helvetica", 10)
            )
            info_label.pack(pady=2)

            select_button = tk.Button(
                card_frame,
                text="Select",
                command=lambda c=card: self.select_and_close(c, event, window),
                width=12,
                bg="#4CAF50",
                fg="white",
                font=("Helvetica", 10, "bold"),
            )
            select_button.pack(pady=5)

        # Configure grid columns
        for i in range(COLUMNS):
            content_frame.grid_columnconfigure(i, weight=1)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure canvas size when window resizes
        def configure_canvas(event):
            canvas.itemconfig(canvas_frame, width=event.width)

        canvas.bind("<Configure>", configure_canvas)

        # Bind mousewheel scrolling
        def on_mousewheel(event):
            if canvas.winfo_exists():  # Check if canvas still exists
                canvas.yview_scroll(-1 * (event.delta // 120), "units")

        # Bind mousewheel only when mouse is over the canvas
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Clean up bindings when window is closed
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", on_closing)

    def select_and_close(self, card, event, window):
        self.selected_card = card
        self.log_message(f"UI Selected card: {card['name']}")
        event.set()
        window.destroy()
