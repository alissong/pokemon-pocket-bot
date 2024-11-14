# src/views/ui.py

import os
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
from views.region_capture import RegionCaptureUI

# Constants and Configuration
UI_COLORS = {
    "bg": "#2E3440",
    "fg": "#D8DEE9",
    "accent": "#81A1C1",
    "button_bg": "#4C566A",
    "entry_bg": "#3B4252",
    "entry_fg": "#D8DEE9",
    "success": "#27AE60",  # Green
    "error": "#E74C3C",  # Red
    "warning": "#F39C12",  # Orange
    "info": "#2196F3",  # Blue
}

UI_FONTS = {
    "header": ("Consolas", 16, "bold"),
    "text": ("Consolas", 10),
    "small": ("Helvetica", 8),
}

WINDOW_CONFIG = {"width": 900, "height": 700, "title": "Pokemon Pocket Bot"}

GAME_STATE_CONFIG = {
    "refresh_interval": 1000,  # ms
    "text_height": {"active": 2, "hand": 8, "bench": 8},
    "text_width": {"hand": 20, "bench": 20, "log": 35},
}

CARD_PROMPT_CONFIG = {
    "timeout": 12,  # seconds
    "max_image_height": 400,
    "window_size": "400x600",
}

CARD_OPTIONS_CONFIG = {
    "window_size": "700x700",
    "columns": 3,
    "card_dimensions": (150, 210),  # width, height
    "max_zoomed_height": 200,
}


class BotUI:
    def __init__(self, root, app_state):
        self.root = root
        self.app_state = app_state
        self.root.title(WINDOW_CONFIG["title"])
        self.config_manager = ConfigManager()
        self.debug_window = DebugWindow(root)
        self.bot = PokemonBot(app_state, self.log_message, self)

        # Initialize state variables
        self.bot_running = False
        self.card_name_event = None
        self.card_name = None
        self.selected_card = None
        self.start_x_entry = None
        self.start_y_entry = None
        self.width_entry = None
        self.height_entry = None

        self.setup_ui()
        self.load_configs()

        # Bind the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Update window size
        self.root.geometry(f"{WINDOW_CONFIG['width']}x{WINDOW_CONFIG['height']}")
        self.root.configure(bg=UI_COLORS["bg"])

        # Set dark theme colors
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]
        accent_color = UI_COLORS["accent"]
        button_bg_color = UI_COLORS["button_bg"]
        entry_bg_color = UI_COLORS["entry_bg"]
        entry_fg_color = UI_COLORS["entry_fg"]
        header_font = UI_FONTS["header"]
        text_font = UI_FONTS["text"]

        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Configuration menu
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuration", menu=config_menu)
        config_menu.add_command(
            label="Select Emulator Path", command=self.select_emulator_path
        )

        # Device menu
        device_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Devices", menu=device_menu)
        device_menu.add_command(
            label="Connect to Device", command=self.show_device_connection_dialog
        )
        device_menu.add_command(label="Refresh Devices", command=self.refresh_devices)
        device_menu.add_separator()
        device_menu.add_command(
            label="Disconnect All", command=self.disconnect_all_devices
        )

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Take Screenshot", command=self.take_screenshot)
        tools_menu.add_command(
            label="Capture Region", command=self.take_region_screenshot
        )
        tools_menu.add_command(label="Debug Window", command=self.toggle_debug_window)

        # Create main container with horizontal layout
        main_container = tk.Frame(self.root, bg=bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create left panel for main controls
        left_panel = tk.Frame(main_container, bg=bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Create right panel for logs
        right_panel = tk.Frame(main_container, bg=bg_color, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_panel.pack_propagate(False)

        # Header
        header_frame = tk.Frame(left_panel, bg=bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header_frame,
            text=WINDOW_CONFIG["title"],
            font=UI_FONTS["header"],
            bg=bg_color,
            fg=UI_COLORS["accent"],
        ).pack(pady=5)

        # Bot Controls Section
        control_frame = self.create_section_frame(
            left_panel, "Bot Controls", bg_color, fg_color, text_font
        )

        button_style = {
            "font": text_font,
            "relief": tk.FLAT,
            "bg": button_bg_color,
            "fg": fg_color,
            "padx": 15,
            "pady": 5,
        }

        self.start_stop_button = tk.Button(
            control_frame, text="Start Bot", command=self.toggle_bot, **button_style
        )
        self.start_stop_button.pack(pady=5)

        # Status Section
        status_frame = self.create_section_frame(
            left_panel, "Status", bg_color, fg_color, text_font
        )

        # Create a container for status and debug button
        status_container = tk.Frame(status_frame, bg=bg_color)
        status_container.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(
            status_container,
            text="Status: Not running",
            font=text_font,
            fg=UI_COLORS["error"],
            bg=bg_color,
        )
        self.status_label.pack(side=tk.LEFT, pady=5)

        # Add debug button
        debug_button = tk.Button(
            status_container,
            text="🔍 Debug",
            command=self.toggle_debug_window,
            font=text_font,
            relief=tk.FLAT,
            bg=button_bg_color,
            fg=fg_color,
            padx=10,
        )
        debug_button.pack(side=tk.RIGHT, padx=5)

        # Selected emulator path display
        self.selected_emulator_label = tk.Label(
            status_frame,
            text="",
            font=text_font,
            bg=entry_bg_color,
            fg=entry_fg_color,
            relief=tk.FLAT,
            padx=5,
        )
        self.selected_emulator_label.pack(fill=tk.X, padx=5, pady=2)

        # Game State Display Section
        game_state_frame = self.create_section_frame(
            left_panel, "Game State Display", bg_color, fg_color, text_font
        )

        # Refresh controls
        refresh_frame = tk.Frame(game_state_frame, bg=bg_color)
        refresh_frame.pack(fill=tk.X, pady=(0, 5))

        self.refresh_button = tk.Button(
            refresh_frame,
            text="🔄 Refresh",
            command=self.update_game_state_display,
            bg=button_bg_color,
            fg=fg_color,
            font=text_font,
            relief=tk.FLAT,
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.auto_refresh_check = tk.Checkbutton(
            refresh_frame,
            text="Auto refresh",
            variable=self.auto_refresh_var,
            bg=bg_color,
            fg=fg_color,
            font=text_font,
            activebackground=bg_color,
            activeforeground=fg_color,
            selectcolor=bg_color,
        )
        self.auto_refresh_check.pack(side=tk.LEFT)

        # Active Pokémon display
        active_frame = tk.Frame(game_state_frame, bg=bg_color)
        active_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(
            active_frame,
            text="Active Pokémon:",
            font=text_font,
            bg=bg_color,
            fg=accent_color,
        ).pack(side=tk.LEFT)
        self.active_text = tk.Text(
            active_frame,
            height=2,
            width=30,
            font=text_font,
            bg=entry_bg_color,
            fg=entry_fg_color,
            relief=tk.FLAT,
        )
        self.active_text.pack(fill=tk.X, padx=5)

        # Hand and Bench columns
        columns_frame = tk.Frame(game_state_frame, bg=bg_color)
        columns_frame.pack(fill=tk.X, expand=True, padx=5, pady=2)

        # Hand column
        hand_frame = tk.Frame(columns_frame, bg=entry_bg_color, relief=tk.FLAT)
        hand_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        tk.Label(
            hand_frame,
            text="Hand",
            font=text_font,
            bg=entry_bg_color,
            fg=accent_color,
        ).pack()
        self.hand_text = tk.Text(
            hand_frame,
            height=GAME_STATE_CONFIG["text_height"]["hand"],
            width=GAME_STATE_CONFIG["text_width"]["hand"],
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["entry_fg"],
            relief=tk.FLAT,
        )
        self.hand_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Bench column
        bench_frame = tk.Frame(columns_frame, bg=entry_bg_color, relief=tk.FLAT)
        bench_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        tk.Label(
            bench_frame,
            text="Bench",
            font=text_font,
            bg=entry_bg_color,
            fg=accent_color,
        ).pack()
        self.bench_text = tk.Text(
            bench_frame,
            height=GAME_STATE_CONFIG["text_height"]["bench"],
            width=GAME_STATE_CONFIG["text_width"]["bench"],
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["entry_fg"],
            relief=tk.FLAT,
        )
        self.bench_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Make all text widgets read-only
        for widget in (self.hand_text, self.active_text, self.bench_text):
            widget.config(state=tk.DISABLED)

        # Log Section
        log_frame = self.create_section_frame(
            right_panel, "Log", bg_color, fg_color, text_font
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Create log text with scrollbar
        log_container = tk.Frame(log_frame, bg=bg_color)
        log_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_container, bg=bg_color, troughcolor=entry_bg_color)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_container,
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["entry_fg"],
            width=GAME_STATE_CONFIG["text_width"]["log"],
            height=40,
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Start the auto-refresh cycle
        self.start_auto_refresh()

    def create_section_frame(self, parent, title, bg_color, fg_color, font):
        """Helper method to create consistent section frames"""
        frame = tk.LabelFrame(
            parent,
            text=title,
            font=font,
            bg=bg_color,
            fg=fg_color,
            pady=5,
            padx=10,
            relief=tk.FLAT,
        )
        frame.pack(fill=tk.X, pady=5)
        return frame

    def create_collapsible_section(self, parent, title, bg_color, fg_color, font):
        """Helper method to create collapsible section frames"""
        frame = tk.LabelFrame(
            parent,
            text=title,
            font=font,
            bg=bg_color,
            fg=fg_color,
            pady=0,
            padx=5,
            relief=tk.FLAT,
        )
        frame.pack(fill=tk.X, pady=1)

        content_frame = tk.Frame(frame, bg=bg_color)

        def toggle_section():
            if content_frame.winfo_viewable():
                content_frame.pack_forget()
                toggle_btn.config(text="▼")
                frame.configure(height=20)
            else:
                content_frame.pack(fill=tk.X, pady=2)
                toggle_btn.config(text="▲")
                frame.configure(height=0)

        toggle_btn = tk.Button(
            frame,
            text="▼",
            command=toggle_section,
            font=("Helvetica", 8),
            width=2,
            height=1,
            relief=tk.FLAT,
            bg=bg_color,
            fg=fg_color,
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
        """Thread-safe logging method"""
        if not self.root.winfo_exists():
            return

        def _log():
            if not self.root.winfo_exists():
                return
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            # Update game state display whenever we log a message
            self.update_game_state_display()

        # Schedule the log update on the main thread
        self.root.after(0, _log)

    def toggle_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.start_stop_button.config(text="Stop Bot", bg=UI_COLORS["error"])
            self.status_label.config(text="Status: Running", fg=UI_COLORS["success"])
            self.log_message("Bot started.")
            self.bot.start()
        else:
            self.bot.stop()
            self.bot_running = False
            self.start_stop_button.config(text="Start Bot", bg=UI_COLORS["info"])
            self.status_label.config(text="Status: Not running", fg=UI_COLORS["error"])
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
        # Take a screenshot first
        screenshot = take_screenshot()
        if screenshot is not None:
            # Create and show the region capture UI
            capture_ui = RegionCaptureUI(screenshot)
            region = capture_ui.get_region()

            if region:
                # Take the actual region screenshot
                region_screenshot = self.bot.image_processor.capture_region(region)

                # Ensure images directory exists
                images_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(images_dir, exist_ok=True)

                # Ask user where to save the file
                file_path = filedialog.asksaveasfilename(
                    initialdir=images_dir,
                    defaultextension=".PNG",
                    filetypes=[
                        ("PNG files", "*.png"),
                        ("JPEG files", "*.jpg"),
                        ("All files", "*.*"),
                    ],
                    title="Save Region Screenshot",
                )

                if file_path:
                    # Save the screenshot
                    cv2.imwrite(file_path, region_screenshot)
                    self.log_message(f"Region screenshot saved to: {file_path}")
                else:
                    self.log_message("Region screenshot capture cancelled.")

    def request_card_name(self, image, event, error_message=None):
        self.card_name_event = event
        self.card_name = None  # Reset card_name
        self.root.after(0, self.show_card_prompt, image, error_message)

    def show_card_prompt(self, image, error_message=None):
        window = tk.Toplevel(self.root)
        window.title("Unknown Card")
        window.geometry(CARD_PROMPT_CONFIG["window_size"])

        # Add timeout label
        timeout_label = tk.Label(
            window,
            text=f"Time remaining: {CARD_PROMPT_CONFIG['timeout']}s",
            fg=UI_COLORS["error"],
        )
        timeout_label.pack(pady=5)

        # Timeout counter
        remaining_time = CARD_PROMPT_CONFIG["timeout"]

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
        max_height = CARD_PROMPT_CONFIG["max_image_height"]

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
        window.geometry(CARD_OPTIONS_CONFIG["window_size"])

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
        max_height = CARD_OPTIONS_CONFIG["max_zoomed_height"]
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
        COLUMNS = CARD_OPTIONS_CONFIG["columns"]
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
            api_card_image = cv2.resize(
                api_card_image, CARD_OPTIONS_CONFIG["card_dimensions"]
            )
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
            self.root.after(GAME_STATE_CONFIG["refresh_interval"], refresh_cycle)

        # Start the first refresh cycle
        self.root.after(GAME_STATE_CONFIG["refresh_interval"], refresh_cycle)

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

    def on_closing(self):
        if self.bot_running:
            self.bot.stop()
            self.bot_running = False
        # Set the event to prevent blocking
        if self.card_name_event:
            self.card_name_event.set()
        self.root.destroy()

    def show_device_connection_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Device Connection Manager")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()

        # Connection status frame
        status_frame = tk.LabelFrame(
            dialog, text="Connection Status", font=UI_FONTS["text"]
        )
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        current_device = tk.Label(
            status_frame,
            text=f"Current device: {self.app_state.emulator_name or 'None'}",
            font=UI_FONTS["text"],
        )
        current_device.pack(pady=5)

        connection_status = tk.Label(
            status_frame,
            text="Status: Not connected",
            font=UI_FONTS["text"],
            fg=UI_COLORS["warning"],
        )
        connection_status.pack(pady=5)

        # Device list frame
        device_frame = tk.LabelFrame(
            dialog, text="Available Devices", font=UI_FONTS["text"]
        )
        device_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        devices_list = tk.Listbox(
            device_frame, font=UI_FONTS["text"], selectmode=tk.SINGLE
        )
        devices_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(device_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        devices_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=devices_list.yview)

        def refresh_device_list():
            devices_list.delete(0, tk.END)
            devices = self.bot.emulator_controller.get_all_devices()

            if not devices:
                connection_status.config(
                    text="Status: No devices found", fg=UI_COLORS["error"]
                )
                return

            for device in devices:
                state_text = (
                    "✓ Connected" if device["state"] == "device" else "✗ Disconnected"
                )
                is_current = (
                    " (Current)" if device["id"] == self.app_state.emulator_name else ""
                )
                devices_list.insert(
                    tk.END, f"{device['id']} - {state_text}{is_current}"
                )

                if (
                    device["id"] == self.app_state.emulator_name
                    and device["state"] == "device"
                ):
                    connection_status.config(
                        text=f"Status: Connected to {device['id']}",
                        fg=UI_COLORS["success"],
                    )
                elif device["state"] == "device":
                    connection_status.config(
                        text="Status: Device available", fg=UI_COLORS["info"]
                    )

        def connect_selected():
            selection = devices_list.curselection()
            if not selection:
                connection_status.config(
                    text="Status: Please select a device", fg=UI_COLORS["warning"]
                )
                return

            device_str = devices_list.get(selection[0])
            device_id = device_str.split(" - ")[0].strip()

            connection_status.config(
                text=f"Status: Connecting to {device_id}...", fg=UI_COLORS["info"]
            )
            dialog.update()

            if self.bot.emulator_controller.connect_to_device(device_id):
                connection_status.config(
                    text=f"Status: Connected to {device_id}", fg=UI_COLORS["success"]
                )
                current_device.config(text=f"Current device: {device_id}")
                refresh_device_list()  # Refresh to show updated status
            else:
                connection_status.config(
                    text="Status: Connection failed", fg=UI_COLORS["error"]
                )

        def disconnect_current():
            if not self.app_state.emulator_name:
                connection_status.config(
                    text="Status: No device connected", fg=UI_COLORS["warning"]
                )
                return

            self.bot.emulator_controller.disconnect_all_devices()
            self.app_state.emulator_name = None
            current_device.config(text="Current device: None")
            connection_status.config(text="Status: Disconnected", fg=UI_COLORS["info"])
            refresh_device_list()

        # Buttons frame
        buttons_frame = tk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        # Add buttons with improved styling
        refresh_btn = tk.Button(
            buttons_frame,
            text="🔄 Refresh",
            command=refresh_device_list,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            width=12,
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        connect_btn = tk.Button(
            buttons_frame,
            text="🔌 Connect",
            command=connect_selected,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            width=12,
        )
        connect_btn.pack(side=tk.LEFT, padx=5)

        disconnect_btn = tk.Button(
            buttons_frame,
            text="⚡ Disconnect",
            command=disconnect_current,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            width=12,
        )
        disconnect_btn.pack(side=tk.LEFT, padx=5)

        close_btn = tk.Button(
            buttons_frame,
            text="✖ Close",
            command=dialog.destroy,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            width=12,
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

        # Manual connection frame
        manual_frame = tk.LabelFrame(
            dialog, text="Manual Connection", font=UI_FONTS["text"]
        )
        manual_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(manual_frame, text="IP:Port", font=UI_FONTS["text"]).pack(
            side=tk.LEFT, padx=5
        )
        ip_entry = tk.Entry(manual_frame, font=UI_FONTS["text"])
        ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        manual_connect_btn = tk.Button(
            manual_frame,
            text="Connect",
            command=lambda: connect_manual(),
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
        )
        manual_connect_btn.pack(side=tk.RIGHT, padx=5)

        def connect_manual():
            ip_port = ip_entry.get().strip()
            if not ip_port:
                connection_status.config(
                    text="Status: Please enter IP:Port", fg=UI_COLORS["warning"]
                )
                return

            if self.bot.emulator_controller.connect_to_device(ip_port):
                connection_status.config(
                    text=f"Status: Connected to {ip_port}", fg=UI_COLORS["success"]
                )
                current_device.config(text=f"Current device: {ip_port}")
                refresh_device_list()
            else:
                connection_status.config(
                    text="Status: Connection failed", fg=UI_COLORS["error"]
                )

        refresh_device_list()  # Initial population

    def refresh_devices(self):
        devices = self.bot.emulator_controller.get_all_devices()
        self.log_message("Available devices:")
        for device in devices:
            self.log_message(f"• {device['id']} - {device['state']}")

    def disconnect_all_devices(self):
        self.bot.emulator_controller.disconnect_all_devices()
        self.log_message("Disconnected all devices")
