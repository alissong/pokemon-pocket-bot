import tkinter as tk

from bot import PokemonBot
from utils.config_manager import ConfigManager
from views.components.section_frame import SectionFrame
from views.debug_window import DebugWindow
from views.dialogs.card_options_dialog import CardOptionsDialog
from views.dialogs.card_prompt_dialog import CardPromptDialog
from views.themes import (
    CARD_OPTIONS_CONFIG,
    CARD_PROMPT_CONFIG,
    UI_COLORS,
    UI_FONTS,
    WINDOW_CONFIG,
)

from .menu_builder import MenuBuilder
from .sections.control_section import ControlSection
from .sections.game_state_section import GameStateSection
from .sections.log_section import LogSection
from .sections.status_section import StatusSection
from .ui_actions import UIActions


class BotUI:
    def __init__(self, root, app_state):
        self.root = root
        self.app_state = app_state
        self.config_manager = ConfigManager()
        self.debug_window = DebugWindow(root)

        # Initialize the bot before ui_actions
        self.bot = PokemonBot(app_state, self.log_message_proxy, self)
        self.ui_actions = UIActions(self)

        # Initialize state variables
        self.bot_running = False
        self.card_name_event = None
        self.card_name = None
        self.selected_card = None

        self.setup_ui()
        self.load_configs()

        # Bind the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.ui_actions.on_closing)

    def log_message_proxy(self, message):
        """Proxy method to forward log messages to the log section"""
        if hasattr(self, "log_section"):
            self.log_section.log_message(message)

    def setup_ui(self):
        # Set dark theme colors
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]
        accent_color = UI_COLORS["accent"]
        button_bg_color = UI_COLORS["button_bg"]
        entry_bg_color = UI_COLORS["entry_bg"]
        entry_fg_color = UI_COLORS["entry_fg"]
        header_font = UI_FONTS["header"]
        text_font = UI_FONTS["text"]

        # Update window size
        self.root.geometry(f"{WINDOW_CONFIG['width']}x{WINDOW_CONFIG['height']}")
        self.root.configure(bg=UI_COLORS["bg"])
        self.root.title("Pokemon Pocket Bot")

        # Setup menu
        MenuBuilder(self).build()

        # Create main container
        main_container = tk.Frame(self.root, bg=bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create panels
        left_panel = tk.Frame(main_container, bg=bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_panel = tk.Frame(main_container, bg=bg_color, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_panel.pack_propagate(False)

        # Create header
        self._create_header(left_panel)

        # Initialize sections
        self.control_section = ControlSection(left_panel, self)
        self.status_section = StatusSection(left_panel, self)
        self.game_state_section = GameStateSection(left_panel, self)
        self.log_section = LogSection(right_panel, self)

        # Start the auto-refresh cycle
        self.game_state_section.start_auto_refresh()

    def _create_header(self, parent):
        header_frame = tk.Frame(parent, bg=UI_COLORS["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header_frame,
            text=WINDOW_CONFIG["title"],
            font=UI_FONTS["header"],
            bg=UI_COLORS["bg"],
            fg=UI_COLORS["accent"],
        ).pack(pady=5)

    def load_configs(self):
        config = self.config_manager.load()
        if config:
            self.app_state.update(config)
            self.status_section.update_emulator_path(self.app_state.program_path)

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
        self.log_section.log_message(f"UI Selected card: {card['name']}")
        event.set()

    def create_section_frame(self, parent, title):
        """Helper method to create consistent section frames"""
        return SectionFrame(parent, title)
