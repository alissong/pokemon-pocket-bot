import tkinter as tk

from views.components.section_frame import SectionFrame
from views.themes import GAME_STATE_CONFIG, UI_COLORS, UI_FONTS


class GameStateSection:
    def __init__(self, parent, bot_ui):
        self.bot_ui = bot_ui
        self.section = SectionFrame(parent, "Game State Display")
        self.section.frame.pack(fill=tk.X, pady=5)
        self.setup_game_state()

    def setup_game_state(self):
        # Refresh controls
        refresh_frame = tk.Frame(self.section.frame, bg=UI_COLORS["bg"])
        refresh_frame.pack(fill=tk.X, pady=(0, 5))

        self.refresh_button = tk.Button(
            refresh_frame,
            text="🔄 Refresh",
            command=self.update_display,
            bg=UI_COLORS["button_bg"],
            fg=UI_COLORS["fg"],
            font=UI_FONTS["text"],
            relief=tk.FLAT,
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.auto_refresh_check = tk.Checkbutton(
            refresh_frame,
            text="Auto refresh",
            variable=self.auto_refresh_var,
            bg=UI_COLORS["bg"],
            fg=UI_COLORS["fg"],
            font=UI_FONTS["text"],
            activebackground=UI_COLORS["bg"],
            activeforeground=UI_COLORS["fg"],
            selectcolor=UI_COLORS["bg"],
        )
        self.auto_refresh_check.pack(side=tk.LEFT)

        # Active Pokémon display
        active_frame = tk.Frame(self.section.frame, bg=UI_COLORS["bg"])
        active_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(
            active_frame,
            text="Active Pokémon:",
            font=UI_FONTS["text"],
            bg=UI_COLORS["bg"],
            fg=UI_COLORS["accent"],
        ).pack(side=tk.LEFT)

        self.active_text = tk.Text(
            active_frame,
            height=GAME_STATE_CONFIG["text_height"]["active"],
            width=30,
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["entry_fg"],
            relief=tk.FLAT,
        )
        self.active_text.pack(fill=tk.X, padx=5)
        self.active_text.config(state=tk.DISABLED)

        # Hand and Bench columns
        columns_frame = tk.Frame(self.section.frame, bg=UI_COLORS["bg"])
        columns_frame.pack(fill=tk.X, expand=True, padx=5, pady=2)

        # Hand column
        self.setup_hand_column(columns_frame)

        # Bench column
        self.setup_bench_column(columns_frame)

    def setup_hand_column(self, parent):
        hand_frame = tk.Frame(parent, bg=UI_COLORS["entry_bg"], relief=tk.FLAT)
        hand_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)

        tk.Label(
            hand_frame,
            text="Hand",
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["accent"],
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

    def setup_bench_column(self, parent):
        bench_frame = tk.Frame(parent, bg=UI_COLORS["entry_bg"], relief=tk.FLAT)
        bench_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)

        tk.Label(
            bench_frame,
            text="Bench",
            font=UI_FONTS["text"],
            bg=UI_COLORS["entry_bg"],
            fg=UI_COLORS["accent"],
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

    def start_auto_refresh(self):
        def refresh_cycle():
            if self.auto_refresh_var.get():
                self.update_display()
            self.bot_ui.root.after(GAME_STATE_CONFIG["refresh_interval"], refresh_cycle)

        self.bot_ui.root.after(GAME_STATE_CONFIG["refresh_interval"], refresh_cycle)

    def update_display(self):
        try:
            game_state = self.bot_ui.bot.game_state

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
            self.bot_ui.log_section.log_message(
                f"Error updating game state display: {e}"
            )
