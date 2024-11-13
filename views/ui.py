# src/views/ui.py

import tkinter as tk
from tkinter import filedialog

import cv2
import numpy as np
import requests
from PIL import Image, ImageTk

from bot import PokemonBot
from utils.adb_utils import take_screenshot
from utils.config_manager import ConfigManager
from views.debug_window import DebugWindow


class BotUI:
    def __init__(self, root, app_state):
        self.root = root
        self.app_state = app_state
        self.root.title("Pokemon Pocket Bot")
        self.config_manager = ConfigManager()
        self.debug_window = DebugWindow(root)
        self.bot = PokemonBot(app_state, self.log_message, self)

        self.bot_running = False

        self.card_name_event = None
        self.card_name = None
        self.selected_card = None

        # Initialize entry variables
        self.start_x_entry = None
        self.start_y_entry = None
        self.width_entry = None
        self.height_entry = None

        self.setup_ui()
        self.load_configs()

    def setup_ui(self):
        # Update window size for wider layout
        self.root.geometry(
            "800x700"
        )  # Increased width further to better accommodate both panels

        # Create main container with horizontal layout
        main_container = tk.Frame(self.root, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create left panel for main controls (increase relative space)
        left_panel = tk.Frame(main_container, bg="#f0f0f0")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Create right panel for logs (adjust width)
        right_panel = tk.Frame(main_container, bg="#f0f0f0", width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_panel.pack_propagate(False)

        # Simplified header with less space
        header_frame = tk.Frame(left_panel, bg="#f0f0f0")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header_frame,
            text="Pokemon Pocket Bot ⚔️",
            font=("Helvetica", 16, "bold"),  # Reduced font size
            bg="#f0f0f0",
            fg="#2C3E50",
        ).pack(pady=5)  # Reduced padding

        # Make main_container expand vertically
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create sections with distinct grouping
        # Path Selection Section
        path_frame = self.create_section_frame(left_panel, "Emulator Configuration")

        self.select_path_button = tk.Button(
            path_frame,
            text="Select Emulator Path",
            command=self.select_emulator_path,
            font=("Helvetica", 10),
            bg="#4CAF50",
            fg="white",
            relief=tk.FLAT,
            padx=10,
        )
        self.select_path_button.pack(side=tk.LEFT, padx=5)

        self.selected_emulator_label = tk.Label(
            path_frame,
            text="",
            font=("Helvetica", 10),
            bg="white",
            relief=tk.SUNKEN,
            padx=5,
        )
        self.selected_emulator_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Control Section
        control_frame = self.create_section_frame(left_panel, "Bot Controls")

        button_style = {
            "font": ("Helvetica", 10, "bold"),
            "relief": tk.FLAT,
            "padx": 15,
            "pady": 5,
        }

        self.start_stop_button = tk.Button(
            control_frame,
            text="Start Bot",
            command=self.toggle_bot,
            bg="#2196F3",
            fg="white",
            **button_style,
        )
        self.start_stop_button.pack(side=tk.LEFT, padx=5)

        self.debug_button = tk.Button(
            control_frame,
            text="Debug Window",
            command=self.toggle_debug_window,
            bg="#FF9800",
            fg="white",
            **button_style,
        )
        self.debug_button.pack(side=tk.LEFT, padx=5)

        # Screenshot Section
        screenshot_frame = self.create_section_frame(left_panel, "Screenshot Tools")

        self.screenshot_button = tk.Button(
            screenshot_frame,
            text="Take Screenshot",
            command=self.take_screenshot,
            bg="#9C27B0",
            fg="white",
            **button_style,
        )
        self.screenshot_button.pack(side=tk.LEFT, padx=5)

        # Define entry style before region selection section
        entry_style = {
            "width": 8,
            "font": ("Helvetica", 10),
            "relief": tk.SUNKEN,
            "bg": "white",
        }

        # Region Selection Section
        region_frame = self.create_collapsible_section(left_panel, "Region Selection")

        # Move region selection content to a separate frame
        coords_frame = tk.Frame(region_frame, bg="#f0f0f0")
        coords_frame.pack(fill=tk.X)

        # Add coordinate inputs with better layout
        for i, (label, var) in enumerate(
            [
                ("Start X:", self.start_x_entry),
                ("Start Y:", self.start_y_entry),
                ("Width:", self.width_entry),
                ("Height:", self.height_entry),
            ]
        ):
            tk.Label(
                coords_frame, text=label, font=("Helvetica", 10), bg="#f0f0f0"
            ).grid(row=i // 2, column=i % 2 * 2, padx=5, pady=3)

            entry = tk.Entry(coords_frame, **entry_style)
            entry.grid(row=i // 2, column=i % 2 * 2 + 1, padx=5, pady=3)
            setattr(self, f"{var}", entry)

        self.region_screenshot_button = tk.Button(
            coords_frame,
            text="Capture Region",
            command=self.take_region_screenshot,
            bg="#9C27B0",
            fg="white",
            **button_style,
        )
        self.region_screenshot_button.grid(row=2, column=0, columnspan=4, pady=5)

        # Status Section
        status_frame = self.create_section_frame(left_panel, "Status")

        self.status_label = tk.Label(
            status_frame,
            text="Status: Not running",
            font=("Helvetica", 10, "bold"),
            fg="#E74C3C",
            bg="#f0f0f0",
        )
        self.status_label.pack(pady=5)

        # Add Game State Display Section with refresh button
        game_state_frame = self.create_section_frame(left_panel, "Game State Display")

        # Add refresh controls
        refresh_frame = tk.Frame(game_state_frame, bg="#f0f0f0")
        refresh_frame.pack(fill=tk.X, pady=(0, 5))

        self.refresh_button = tk.Button(
            refresh_frame,
            text="🔄 Refresh",
            command=self.update_game_state_display,
            bg="#4CAF50",
            fg="white",
            font=("Helvetica", 9),
            relief=tk.FLAT,
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.auto_refresh_check = tk.Checkbutton(
            refresh_frame,
            text="Auto refresh",
            variable=self.auto_refresh_var,
            bg="#f0f0f0",
            font=("Helvetica", 9),
        )
        self.auto_refresh_check.pack(side=tk.LEFT)

        # Active Pokémon display at the top
        active_frame = tk.Frame(game_state_frame, bg="#f0f0f0")
        active_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(
            active_frame,
            text="Active Pokémon:",
            font=("Helvetica", 10, "bold"),
            bg="#f0f0f0",
        ).pack(side=tk.LEFT)
        self.active_text = tk.Text(
            active_frame, height=2, width=30, font=("Consolas", 9)
        )
        self.active_text.pack(fill=tk.X, padx=5)

        # Create two columns for hand and bench
        columns_frame = tk.Frame(game_state_frame, bg="#f0f0f0")
        columns_frame.pack(fill=tk.X, expand=True, padx=5, pady=2)

        # Hand column
        hand_frame = tk.Frame(columns_frame, bg="white", relief=tk.GROOVE, bd=2)
        hand_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        tk.Label(
            hand_frame, text="Hand", font=("Helvetica", 10, "bold"), bg="white"
        ).pack()
        self.hand_text = tk.Text(hand_frame, height=8, width=20, font=("Consolas", 9))
        self.hand_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Bench column
        bench_frame = tk.Frame(columns_frame, bg="white", relief=tk.GROOVE, bd=2)
        bench_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        tk.Label(
            bench_frame, text="Bench", font=("Helvetica", 10, "bold"), bg="white"
        ).pack()
        self.bench_text = tk.Text(bench_frame, height=8, width=20, font=("Consolas", 9))
        self.bench_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Make all text widgets read-only
        for widget in (self.hand_text, self.active_text, self.bench_text):
            widget.config(state=tk.DISABLED)

        # Log Section
        log_frame = self.create_section_frame(right_panel, "Log")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Create log text with scrollbar
        log_container = tk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_container,
            font=("Consolas", 9),
            bg="white",
            width=35,
            height=40,
            wrap=tk.WORD,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Start the auto-refresh cycle
        self.start_auto_refresh()

    def create_section_frame(self, parent, title):
        """Helper method to create consistent section frames"""
        frame = tk.LabelFrame(
            parent,
            text=title,
            font=("Helvetica", 11, "bold"),
            bg="#f0f0f0",
            fg="#34495E",
            pady=5,
            padx=10,
        )
        frame.pack(fill=tk.X, pady=5)
        return frame

    def create_collapsible_section(self, parent, title):
        """Helper method to create collapsible section frames"""
        # Create a frame without padding to minimize height
        frame = tk.LabelFrame(
            parent,
            text=title,
            font=("Helvetica", 11, "bold"),
            bg="#f0f0f0",
            fg="#34495E",
            pady=0,  # Removed padding
            padx=5,  # Minimal padding
        )
        frame.pack(fill=tk.X, pady=1)  # Reduced outer padding

        # Create a container for the content
        content_frame = tk.Frame(frame, bg="#f0f0f0")

        def toggle_section():
            if content_frame.winfo_viewable():
                content_frame.pack_forget()
                toggle_btn.config(text="▼")
                # Minimize frame height when collapsed
                frame.configure(height=20)
            else:
                content_frame.pack(fill=tk.X, pady=2)  # Reduced inner padding
                toggle_btn.config(text="▲")
                frame.configure(height=0)  # Let it expand naturally when open

        # Make toggle button smaller and more compact
        toggle_btn = tk.Button(
            frame,
            text="▼",
            command=toggle_section,
            font=("Helvetica", 6),  # Smaller font
            width=1,  # Smaller width
            height=1,  # Smaller height
            relief=tk.FLAT,
            padx=1,
            pady=0,
        )
        toggle_btn.pack(side=tk.RIGHT, padx=2, pady=0)

        return content_frame

    def toggle_debug_window(self):
        if (
            self.debug_window.window is None
            or not self.debug_window.window.winfo_viewable()
        ):
            # Get main window's position and size
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_height = self.root.winfo_height()
            self.debug_window.open_window(main_x, main_y, main_height)
        else:
            self.debug_window.close_window()

    def load_configs(self):
        config = self.config_manager.load()
        if config:
            self.app_state.update(config)
            self.selected_emulator_label.config(text=self.app_state.program_path)

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        # Update game state display whenever we log a message
        self.update_game_state_display()

    def toggle_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.start_stop_button.config(
                text="Stop Bot",
                bg="#E74C3C",  # Red for stop
            )
            self.status_label.config(
                text="Status: Running",
                fg="#27AE60",  # Green for running
            )
            self.log_message("Bot started.")
            self.bot.start()
        else:
            self.bot.stop()
            self.bot_running = False
            self.start_stop_button.config(
                text="Start Bot",
                bg="#2196F3",  # Blue for start
            )
            self.status_label.config(
                text="Status: Not running",
                fg="#E74C3C",  # Red for not running
            )
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
        timeout_label = tk.Label(window, text="Time remaining: 12s", fg="red")
        timeout_label.pack(pady=5)

        # Timeout counter
        remaining_time = 12

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

    def start_auto_refresh(self):
        """Start the automatic refresh cycle"""

        def refresh_cycle():
            if self.auto_refresh_var.get():
                self.update_game_state_display()
            # Schedule the next refresh in 1 second
            self.root.after(1000, refresh_cycle)

        # Start the first refresh cycle
        self.root.after(1000, refresh_cycle)

    def update_game_state_display(self):
        """Update the game state display with current information"""
        try:
            game_state = self.bot.game_state

            # Update hand display
            self.hand_text.config(state=tk.NORMAL)
            self.hand_text.delete(1.0, tk.END)
            for card in game_state.hand_state:
                self.hand_text.insert(tk.END, f"• {card['name']}\n")
            self.hand_text.config(state=tk.DISABLED)

            # Update active Pokémon display
            self.active_text.config(state=tk.NORMAL)
            self.active_text.delete(1.0, tk.END)
            for pokemon in game_state.active_pokemon:
                self.active_text.insert(tk.END, f"⚔️ {pokemon['name']}\n")
                if "energies" in pokemon:
                    self.active_text.insert(
                        tk.END, f"  ⚡ Energy: {pokemon['energies']}\n"
                    )
            self.active_text.config(state=tk.DISABLED)

            # Update bench display
            self.bench_text.config(state=tk.NORMAL)
            self.bench_text.delete(1.0, tk.END)
            for slot, pokemon in game_state.bench_pokemon.items():
                if pokemon:
                    self.bench_text.insert(tk.END, f"[{slot+1}] {pokemon['name']}\n")
                    if "energies" in pokemon:
                        self.bench_text.insert(
                            tk.END, f"    ⚡ Energy: {pokemon['energies']}\n"
                        )
                else:
                    self.bench_text.insert(tk.END, f"[{slot+1}] Empty\n")
            self.bench_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error updating game state display: {e}")
