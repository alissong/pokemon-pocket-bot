# src/controllers/game_controller.py

import threading
import time

from utils.adb_utils import click_position, drag_position, take_screenshot
from utils.constants import (
    bench_positions,
    card_offset_mapping,
    default_pokemon_stats,  # Add this import
)

card_effects = {
    "professor's research": lambda hand_size: 2,  # Draw 2 (+2)
    "poké ball": lambda hand_size: 1,  # Search and add one base Pokemon card (+1)
}


class GameController:
    def __init__(
        self,
        app_state,
        emulator_controller,
        battle_controller,
        image_processor,
        card_recognition_service,
        game_state,
        template_images,
        log_callback,
    ):
        self.app_state = app_state
        self.emulator_controller = emulator_controller
        self.battle_controller = battle_controller
        self.image_processor = image_processor
        self.card_recognition_service = card_recognition_service
        self.game_state = game_state
        self.template_images = template_images
        self.log_callback = log_callback
        self.running = False

        ## COORDS
        self.zoom_card_region = (80, 255, 740, 1020)
        self.turn_check_region = (50, 1560, 200, 20)
        self.center_x = 400
        self.center_y = 900
        self.card_start_x = 510
        self.card_y = 1500
        self.number_of_cards_region = (790, 1325, 60, 50)

    def start(self):
        if not self.app_state.program_path:
            self.log_callback("Please select emulator path first.")
            return
        self.running = True
        threading.Thread(target=self.run).start()

    def stop(self):
        self.running = False

    def run(self):
        self.emulator_controller.connect_and_run()
        while self.running:
            self.prepare_for_battle()
            self.navigate_to_battle()
            self.start_battle()
            self.handle_battle()
            self.end_battle()

    def prepare_for_battle(self):
        self.game_state.reset()

    def navigate_to_battle(self):
        screenshot = take_screenshot()
        if not self.image_processor.check_and_click(
            screenshot,
            self.template_images["BATTLE_ALREADY_SCREEN"],
            "Battle already screen",
        ):
            self.image_processor.check_and_click(
                screenshot, self.template_images["BATTLE_SCREEN"], "Battle screen"
            )
        time.sleep(4)
        self.battle_controller.perform_search_battle_actions(
            self.running, self.stop, run_event=True
        )

    def start_battle(self):
        self.image_processor.check_and_click_until_found(
            self.template_images["TIME_LIMIT_INDICATOR"],
            "Time limit indicator",
            self.running,
            self.stop,
        )
        time.sleep(3)

    def handle_battle(self):
        while self.running:
            screenshot = take_screenshot()
            if self.is_battle_over(screenshot) or self.next_step_available(screenshot):
                break

            # Handle situations like defeated Pokémon or special cards
            self.click_bench_pokemons()
            self.check_active_pokemon()
            self.reset_view()

            is_turn, self.game_state.is_first_turn, self.game_state.go_first = (
                self.battle_controller.check_turn(
                    self.turn_check_region, self.running, self.game_state
                )
            )
            time.sleep(1)  # wait to draw the card if need
            if is_turn and self.game_state.active_pokemon:
                self.update_game_state()
                self.play_turn()
                self.end_turn()
            elif is_turn:
                self.update_game_state()
                self.process_hand_cards()
                time.sleep(1)
                if self.game_state.is_first_turn:
                    self.image_processor.check_and_click_until_found(
                        self.template_images.get("START_BATTLE_BUTTON"),
                        "Start battle button",
                        self.running,
                        self.stop,
                        similarity_threshold=0.5,
                        max_attempts=10,
                    )
                    self.game_state.first_turn_done = True
            if self.game_state.go_first and self.game_state.first_turn_done:
                self.game_state.go_first = False
                self.log_callback("Played first!")
            else:
                self.log_callback("Waiting for opponent's turn...")
                time.sleep(1)

    def update_game_state(self, cards_delta=0):
        self.reset_view()
        self.check_number_of_cards(cards_delta)
        self.reset_view()
        if self.game_state.number_of_cards and self.game_state.number_of_cards > 0:
            self.card_recognition_service.check_cards(
                self.game_state.number_of_cards,
                self.card_start_x,
                self.card_y,
                self.game_state.hand_state,
                True,
            )
        else:
            self.game_state.hand_state = []

    def play_turn(self):
        if not self.running:
            return
        self.log_callback("Start playing my turn...")

        if not self.game_state.is_first_turn:
            self.add_energy_to_pokemon()

        if 0 < len(self.game_state.hand_state):
            self.log_callback("Hand state:")
            for card in self.game_state.hand_state:
                self.log_callback(f"{card['name']}")
            time.sleep(1)
            self.process_hand_cards()
            time.sleep(1)
            self.reset_view()
        else:
            self.reset_view()
            self.add_energy_to_pokemon()
            self.try_attack()

    def process_hand_cards(self, recursion_level=0):
        # Prevent infinite recursion
        if recursion_level >= 10:  # Safety limit
            self.log_callback("Maximum card processing depth reached")
            return

        card_offset_x = card_offset_mapping.get(self.game_state.number_of_cards, 20)
        hand_changed = False

        for card in self.game_state.hand_state:
            card_delta = 0

            if self.game_state.is_first_turn and card["info"].get("item_card"):
                self.log_callback(f"Skipping trainer card {card['name']} on first turn")
                continue

            if (
                card["info"].get("item_card")
                and self.game_state.played_trainer_cards >= 2
            ):
                self.log_callback(
                    f"Skipping trainer card {card['name']} because we already played 2"
                )
                continue

            if not self.running:
                return

            start_x = self.card_start_x - (card["position"] * card_offset_x)
            if card["info"].get("item_card"):
                card_delta += self.play_trainer_card(card, start_x)
                hand_changed = True
                break
            elif self.can_set_active_pokemon(card):
                card_delta -= 1  # Placing a Pokémon reduces hand size by 1
                self.set_active_pokemon(card, start_x)
                hand_changed = True
                break
            elif self.can_place_on_bench(card):
                card_delta -= 1  # Placing a Pokémon on bench reduces hand size by 1
                self.place_pokemon_on_bench(card, start_x)
                hand_changed = True
                break
            elif self.can_evolve_pokemon(card):
                card_delta -= 1  # Evolving a Pokémon reduces hand size by 1
                self.evolve_active_pokemon(card, start_x)
                hand_changed = True
                break
            self.reset_view()
        if hand_changed:
            self.reset_view()
            self.update_game_state(cards_delta=card_delta)
            # Only recurse if we still have cards to process
            if (
                self.game_state.hand_state
            ):  ##TODO: maybe check turn again to prevent miss screenshots of the hand
                self.process_hand_cards(recursion_level + 1)
        self.game_state.played_trainer_cards = 0

    def play_trainer_card(self, card, start_x):
        self.log_callback(f"Playing trainer card: {card['name']}...")
        card_name_lower = card["name"].lower()
        # Default effect is we lose one card from hand (playing the card)
        card_delta_effect = -1

        # Check if card effect is in our mapping
        effect_func = card_effects.get(card_name_lower)
        if effect_func:
            card_delta_effect = effect_func(self.game_state.number_of_cards)

        time.sleep(1)
        drag_position((start_x, self.card_y), (self.center_x, self.center_y))
        time.sleep(4)
        self.game_state.played_trainer_cards += 1
        return card_delta_effect

    def can_set_active_pokemon(self, card):
        return (
            not self.game_state.active_pokemon
            and card["info"].get("level") == 0
            and not card["info"].get("item_card", False)
        )

    def set_active_pokemon(self, card, start_x):
        self.log_callback(f"Setting Active Pokémon: {card['name']}")
        self.reset_view()
        time.sleep(0.7)
        drag_position((start_x, self.card_y), (self.center_x, self.center_y - 50))
        ## TODO: Improve this, sometimes is failing maybe because of card_y (the most right card fails)
        self.game_state.active_pokemon.append(card)
        time.sleep(1)
        self.log_callback("Battle Start!")

    def can_place_on_bench(self, card):
        return (
            len(self.game_state.bench_pokemon) < 3
            and card["info"].get("level") == 0
            and not card["info"].get("item_card", False)
            and card["name"]
        )

    def place_pokemon_on_bench(self, card, start_x):
        # Find first empty bench position
        if len(self.game_state.bench_pokemon) >= len(bench_positions):
            return

        bench_position = bench_positions[len(self.game_state.bench_pokemon)]
        self.reset_view()
        time.sleep(1)
        self.log_callback(
            f"Placing card {card['name']} on bench at position {bench_position}..."
        )
        drag_position(
            (start_x, self.card_y),
            (bench_position[0], bench_position[1] - 100),
            1.25,
        )

        bench_pokemon_info = {
            "name": card["name"].capitalize(),
            "info": card["info"],
            "energies": 0,
        }
        self.game_state.bench_pokemon.append(bench_pokemon_info)

    def can_evolve_pokemon(self, card):
        return (
            card["info"].get("evolves_from")
            and self.game_state.active_pokemon
            and card["info"]["evolves_from"].lower()
            == self.game_state.active_pokemon[0]["name"].lower()
            and self.game_state.first_turn_done
            and not self.game_state.go_first
        )

    def evolve_active_pokemon(self, card, start_x):
        self.log_callback(
            f"Evolving {self.game_state.active_pokemon[0]['name']} to {card['name']}..."
        )
        drag_position((start_x, self.card_y), (self.center_x, self.center_y))
        self.game_state.active_pokemon[0] = {
            "name": card["name"],
            "info": card["info"],
            "energies": self.game_state.active_pokemon[0].get("energies", 0),
        }
        time.sleep(1)

    def add_energy_to_pokemon(self):
        if not self.running:
            return
        drag_position((750, 1450), (self.center_x, self.center_y), 0.3)

    def try_attack(self):
        self.add_energy_to_pokemon()
        drag_position((500, 1250), (self.center_x, self.center_y))
        time.sleep(0.25)
        self.reset_view()
        click_position(self.center_x, self.center_y)
        time.sleep(1)
        click_position(540, 1250)
        click_position(540, 1150)
        click_position(540, 1050)
        time.sleep(1)
        click_position(570, 1070)
        self.reset_view()

    def end_turn(self):
        if not self.running:
            return
        self.try_attack()
        self.reset_view()
        time.sleep(0.25)
        screenshot = take_screenshot()
        self.image_processor.check_and_click(
            screenshot, self.template_images["END_TURN"], "End turn"
        )
        time.sleep(0.25)
        self.image_processor.check_and_click(
            screenshot, self.template_images["OK"], "Ok"
        )
        self.game_state.is_first_turn = False  # Ensure we reset the first turn flag

    def end_battle(self):
        time.sleep(4)
        screenshot = take_screenshot()
        if self.image_processor.check_and_click(
            screenshot, self.template_images["TAP_TO_PROCEED_BUTTON"], "Game ended"
        ):
            time.sleep(2)

        max_attempts = 5
        for _ in range(max_attempts):
            screenshot = take_screenshot()
            if self.image_processor.check_and_click(
                screenshot, self.template_images["NEXT_BUTTON"], "Next button"
            ):
                time.sleep(2)
                break
            time.sleep(1)

        for _ in range(max_attempts):
            screenshot = take_screenshot()
            if self.image_processor.check_and_click(
                screenshot, self.template_images["THANKS_BUTTON"], "Thanks button"
            ):
                time.sleep(3)
                break
            time.sleep(1)

        self.image_processor.check_and_click(
            screenshot, self.template_images["CROSS_BUTTON"], "Cross button"
        )

    def is_battle_over(self, screenshot):
        return self.image_processor.check(
            screenshot, self.template_images["TAP_TO_PROCEED_BUTTON"], "Game ended"
        )

    def next_step_available(self, screenshot):
        return (
            self.image_processor.check(
                screenshot, self.template_images["NEXT_BUTTON"], None
            )
            or self.image_processor.check(
                screenshot, self.template_images["THANKS_BUTTON"], None
            )
            or self.image_processor.check(
                screenshot, self.template_images["BATTLE_BUTTON"], None
            )
            or self.image_processor.check(
                screenshot, self.template_images["CROSS_BUTTON"], None
            )
            or self.image_processor.check(
                screenshot, self.template_images["BATTLE_ALREADY_SCREEN"], None
            )
            or self.image_processor.check(
                screenshot, self.template_images["BATTLE_SCREEN"], None
            )
        )

    def check_number_of_cards(self, cards_delta=0):
        if cards_delta != 0:
            self.game_state.number_of_cards += cards_delta
            self.log_callback(
                f"Adjusted number of cards by delta: {cards_delta}, new total: {self.game_state.number_of_cards}"
            )
            return
        if not self.running:
            return
        self.game_state.number_of_cards = None
        n_cards = self.battle_controller.check_number_of_cards(500, 1500)
        if n_cards:
            self.game_state.number_of_cards = int(n_cards)

    def reset_view(self):
        click_position(0, 1350)
        click_position(0, 1350)

    def click_bench_pokemons(self):
        if not self.running:
            return
        self.log_callback("Clicking bench slots...")
        for bench_position in bench_positions:
            click_position(bench_position[0], bench_position[1])

    def check_active_pokemon(self):
        drag_position((500, 1100), (self.center_x, self.center_y))
        zoomed_card_image = self.battle_controller.get_card(
            self.center_x, self.center_y, 1.25
        )
        main_zone_pokemon_id = self.card_recognition_service.identify_card(
            zoomed_card_image
        )
        if main_zone_pokemon_id:
            self.game_state.active_pokemon = []
            card_info = self.card_recognition_service.deck_info.get(
                main_zone_pokemon_id, default_pokemon_stats
            )
            card_info = {
                "name": card_info["name"].capitalize(),
                "info": card_info,
                "energies": 0,
            }
            self.game_state.active_pokemon.append(card_info)
            self.log_callback(f"Active Pokémon: {card_info['name']}")
        else:
            self.game_state.active_pokemon = []
