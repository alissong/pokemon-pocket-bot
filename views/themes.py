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
