import os
import tkinter as tk
from tkinter import filedialog

import cv2

from bot import PokemonBot
from utils.adb_utils import take_screenshot
from utils.config_manager import ConfigManager
from views.components.section_frame import SectionFrame
from views.debug_window import DebugWindow
from views.dialogs.card_options_dialog import CardOptionsDialog
from views.dialogs.card_prompt_dialog import CardPromptDialog
from views.dialogs.device_connection_dialog import DeviceConnectionDialog
from views.region_capture import RegionCaptureUI
from views.themes import (
    CARD_OPTIONS_CONFIG,
    CARD_PROMPT_CONFIG,
    GAME_STATE_CONFIG,
    UI_COLORS,
    UI_FONTS,
    WINDOW_CONFIG,
)


class BotUI:
    def __init__(self, root, app_state):
        self.root = root
        self.app_state = app_state
        self.config_manager = ConfigManager()
        self.debug_window = DebugWindow(root)
        self.bot = PokemonBot(app_state, self.log_message, self)

        # Initialize state variables
        self.bot_running = False
        self.card_name_event = None
        self.card_name = None
        self.selected_card = None

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
        control_section = SectionFrame(left_panel, "Bot Controls")
        control_section.frame.pack(fill=tk.X, pady=5)

        button_style = {
            "font": text_font,
            "relief": tk.FLAT,
            "bg": button_bg_color,
            "fg": fg_color,
            "padx": 15,
            "pady": 5,
        }

        self.start_stop_button = tk.Button(
            control_section.frame,
            text="Start Bot",
            command=self.toggle_bot,
            **button_style,
        )
        self.start_stop_button.pack(pady=5)

        # Status Section
        status_section = SectionFrame(left_panel, "Status")
        status_section.frame.pack(fill=tk.X, pady=5)

        # Create a container for status and debug button
        status_container = tk.Frame(status_section.frame, bg=bg_color)
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
            status_section.frame,
            text="",
            font=text_font,
            bg=entry_bg_color,
            fg=entry_fg_color,
            relief=tk.FLAT,
            padx=5,
        )
        self.selected_emulator_label.pack(fill=tk.X, padx=5, pady=2)

        # Game State Display Section
        game_state_section = SectionFrame(left_panel, "Game State Display")
        game_state_section.frame.pack(fill=tk.X, pady=5)

        # Refresh controls
        refresh_frame = tk.Frame(game_state_section.frame, bg=bg_color)
        refresh_frame.pack(fill=tk.X, pady=(0, 5))

        self.refresh_button = tk.Button(
            refresh_frame,
            text="🔄 Refresh",
            command=self.update_game_state_display,
            bg=UI_COLORS["button_bg"],
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
        active_frame = tk.Frame(game_state_section.frame, bg=bg_color)
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
            height=GAME_STATE_CONFIG["text_height"]["active"],
            width=30,
            font=text_font,
            bg=entry_bg_color,
            fg=entry_fg_color,
            relief=tk.FLAT,
        )
        self.active_text.pack(fill=tk.X, padx=5)
        self.active_text.config(state=tk.DISABLED)

        # Hand and Bench columns
        columns_frame = tk.Frame(game_state_section.frame, bg=bg_color)
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
        self.hand_text.config(state=tk.DISABLED)

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
        self.bench_text.config(state=tk.DISABLED)

        # Log Section
        log_section = SectionFrame(right_panel, "Log")
        log_section.frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create log text with scrollbar
        log_container = tk.Frame(log_section.frame, bg=bg_color)
        log_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(
            log_container, bg=bg_color, troughcolor=UI_COLORS["entry_bg"]
        )
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

    def create_section_frame(self, parent, title):
        """Helper method to create consistent section frames"""
        return SectionFrame(parent, title)

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
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
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
        if screenshot is not None:
            # Save or process the screenshot as needed
            self.log_message("Screenshot taken.")
        else:
            self.log_message("Failed to take screenshot.")

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
            else:
                self.log_message("No region selected for screenshot.")
        else:
            self.log_message("Failed to take screenshot.")

    def request_card_name(self, image, event, error_message=None):
        self.card_name_event = event
        self.card_name = None  # Reset card_name
        CardPromptDialog(
            self.root,
            image,
            event,
            error_message,
            timeout=CARD_PROMPT_CONFIG["timeout"],
            max_image_height=CARD_PROMPT_CONFIG["max_image_height"],
            callback=self.set_card_name,
        )

    def set_card_name(self, card_name):
        self.card_name = card_name

    def show_card_options(self, similarities, zoomed_card_image, event):
        CardOptionsDialog(
            self.root,
            similarities,
            zoomed_card_image,
            lambda c: self.select_card_and_close(c, event),
            max_zoomed_height=CARD_OPTIONS_CONFIG["max_zoomed_height"],
            window_size=CARD_OPTIONS_CONFIG["window_size"],
            columns=CARD_OPTIONS_CONFIG["columns"],
            card_dimensions=CARD_OPTIONS_CONFIG["card_dimensions"],
        )

    def select_card_and_close(self, card, event):
        self.selected_card = card
        self.log_message(f"UI Selected card: {card['name']}")
        event.set()

    def start_auto_refresh(self):
        """Start the automatic refresh cycle"""

        def refresh_cycle():
            if self.auto_refresh_var.get():
                self.update_game_state_display()
            # Schedule the next refresh in configured interval
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
            self.log_message(f"Error updating game state display: {e}")

    def on_closing(self):
        if self.bot_running:
            self.bot.stop()
            self.bot_running = False
        # Set the event to prevent blocking
        if self.card_name_event:
            self.card_name_event.set()
        self.root.destroy()

    def show_device_connection_dialog(self):
        DeviceConnectionDialog(
            self.root,
            self.bot.emulator_controller,
            self.app_state,
            self.log_message,
        )

    def refresh_devices(self):
        devices = self.bot.emulator_controller.get_all_devices()
        self.log_message("Available devices:")
        for device in devices:
            self.log_message(f"• {device['id']} - {device['state']}")

    def disconnect_all_devices(self):
        self.bot.emulator_controller.disconnect_all_devices()
        self.log_message("Disconnected all devices")
