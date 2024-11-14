import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import GAME_STATE_CONFIG, UI_COLORS, UI_FONTS


class GameStateDisplayFrame:
    def __init__(self, parent, controller):
        self.controller = controller
        self.frame = SectionFrame(parent, "Game State Display").frame
        self.setup_display()

    def setup_display(self):
        bg_color = UI_COLORS["bg"]
        fg_color = UI_COLORS["fg"]
        accent_color = UI_COLORS["accent"]
        button_bg_color = UI_COLORS["button_bg"]
        entry_bg_color = UI_COLORS["entry_bg"]
        entry_fg_color = UI_COLORS["entry_fg"]
        text_font = UI_FONTS["text"]

        # Refresh controls
        refresh_frame = tk.Frame(self.frame, bg=bg_color)
        refresh_frame.pack(fill=tk.X, pady=(0, 5))

        self.refresh_button = tk.Button(
            refresh_frame,
            text="🔄 Refresh",
            command=self.update_display,
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
        active_frame = tk.Frame(self.frame, bg=bg_color)
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
        columns_frame = tk.Frame(self.frame, bg=bg_color)
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

    def update_display(self):
        """Update the game state display with current information"""
        try:
            game_state = self.controller.bot.game_state

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
            self.controller.log_message(f"Error updating game state display: {e}")
