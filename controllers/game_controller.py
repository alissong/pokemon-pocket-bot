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
        debug_window=None,
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
        self.card_start_x = 520
        self.card_y = 1485
        self.number_of_cards_region = (790, 1325, 60, 50)
        self.debug_window = debug_window
        self.last_screenshot = None

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

            self.battle_controller.check_rival_afk(screenshot)
            # Add check for rival concede
            self.battle_controller.check_rival_concede(
                screenshot, self.running, self.stop
            )

            is_turn, self.game_state.is_first_turn, self.game_state.go_first = (
                self.battle_controller.check_turn(
                    self.turn_check_region, self.running, self.game_state
                )
            )
            if not self.game_state.is_first_turn:
                # Handle situations like defeated Pokémon or special cards
                self.click_bench_pokemons()
                self.check_active_pokemon()
                self.reset_view()

            time.sleep(3)  # wait to draw the card if need
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
            self.click_bench_pokemons()
            # Add bench state logging here
            self.log_callback("\nBench state:")
            for slot, pokemon in self.game_state.bench_pokemon.items():
                if pokemon:
                    self.log_callback(
                        f"Slot {slot}: {pokemon['name']} (Energy: {pokemon['energies']})"
                    )
                else:
                    self.log_callback(f"Slot {slot}: Empty")

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
            if card in self.game_state.failed_cards:
                continue
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
                played, this_card_delta = self.play_trainer_card(card, start_x)
                if played:
                    card_delta += this_card_delta
                    card_delta -= 1
                    hand_changed = True
                    break
            elif self.can_set_active_pokemon(card):
                if self.set_active_pokemon(card, start_x):
                    hand_changed = True
                    card_delta -= 1  # Placing a Pokémon reduces hand size by 1
                    break
            elif self.can_place_on_bench(card):
                if self.place_pokemon_on_bench(card, start_x):
                    hand_changed = True
                    card_delta -= 1  # Placing a Pokémon on bench reduces hand size by 1
                    break
            elif self.can_evolve_pokemon(card):
                if self.evolve_pokemon(card, start_x):
                    hand_changed = True
                    card_delta -= 1  # Evolving a Pokémon reduces hand size by 1
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
        if recursion_level == 0:
            self.game_state.played_trainer_cards = 0
            self.game_state.failed_cards = []

    def verify_card_play(self, card, start_x, action_func):
        """
        Verifies if a card was successfully played.

        Args:
            card: The card being played
            start_x: Starting x position for the card
            action_func: Function that performs the actual card play action

        Returns:
            bool: True if card was successfully played, False otherwise
        """
        # Store the initial card state
        initial_position = card["position"]
        initial_card_id, _ = self.card_recognition_service.check_specific_card(
            initial_position,
            self.card_start_x,
            self.card_y,
            self.game_state.number_of_cards,
        )

        # Perform the card play action
        action_func()
        time.sleep(4)  # Wait for animation

        # Verify the card was played by checking if it changed
        new_card_id, _ = self.card_recognition_service.check_specific_card(
            initial_position,
            self.card_start_x,
            self.card_y,
            self.game_state.number_of_cards,
        )

        return new_card_id != initial_card_id

    def play_trainer_card(self, card, start_x):
        self.log_callback(f"Playing trainer card: {card['name']}...")
        card_name_lower = card["name"].lower()

        # Define the card play action
        def play_action():
            time.sleep(1)
            self.drag((start_x, self.card_y), (self.center_x, self.center_y))

        # Attempt to play the card and verify success
        if self.verify_card_play(card, start_x, play_action):
            self.game_state.played_trainer_cards += 1
            # Calculate card effect
            effect_func = card_effects.get(card_name_lower)
            if effect_func:
                return True, effect_func(self.game_state.number_of_cards)
            return True, 0  # Default effect: does nothing
        self.game_state.failed_cards.append(card)

        self.log_callback(f"Failed to play trainer card: {card['name']}")
        return False, 0  # No change in hand size if card wasn't played

    def can_set_active_pokemon(self, card):
        return (
            not self.game_state.active_pokemon
            and card["info"].get("level") == 0
            and not card["info"].get("item_card", False)
        )

    def set_active_pokemon(self, card, start_x):
        self.log_callback(f"Setting Active Pokémon: {card['name']}")
        self.reset_view()

        def play_action():
            time.sleep(0.7)
            self.drag((start_x, self.card_y), (self.center_x, self.center_y - 50))

        if self.verify_card_play(card, start_x, play_action):
            self.game_state.active_pokemon.append(card)
            time.sleep(1)
            self.log_callback("Battle Start!")
            return True
        else:
            self.log_callback(f"Failed to set active Pokémon: {card['name']}")
            self.game_state.failed_cards.append(card)
            return False

    def can_place_on_bench(self, card):
        # Count non-None values in bench_pokemon dict
        occupied_slots = sum(
            1 for slot in self.game_state.bench_pokemon.values() if slot is not None
        )
        return (
            occupied_slots < 3
            and card["info"].get("level") == 0
            and not card["info"].get("item_card", False)
            and card["name"]
        )

    def place_pokemon_on_bench(self, card, start_x):
        # Find first empty slot
        empty_slot = next(
            (
                idx
                for idx, pokemon in self.game_state.bench_pokemon.items()
                if pokemon is None
            ),
            None,
        )
        if empty_slot is None:
            return False

        bench_position = bench_positions[empty_slot]
        self.reset_view()

        def play_action():
            time.sleep(1)
            self.log_callback(
                f"Placing card {card['name']} on bench at position {empty_slot}..."
            )
            self.drag(
                (start_x, self.card_y), (bench_position[0], bench_position[1]), 1.25
            )

        if self.verify_card_play(card, start_x, play_action):
            bench_pokemon_info = {
                "name": card["name"].capitalize(),
                "info": card["info"],
                "energies": 0,
            }
            self.game_state.bench_pokemon[empty_slot] = bench_pokemon_info
            return True
        else:
            self.log_callback(f"Failed to place {card['name']} on bench")
            self.game_state.failed_cards.append(card)
            return False

    def can_evolve_pokemon(self, card):
        # Check active pokemon evolution
        if (
            card["info"].get("evolves_from")
            and self.game_state.active_pokemon
            and card["info"]["evolves_from"].lower()
            == self.game_state.active_pokemon[0]["name"].lower()
            and self.game_state.first_turn_done
            and not self.game_state.go_first
        ):
            return True

        # Check bench pokemon evolution
        if card["info"].get("evolves_from"):
            for bench_slot, bench_pokemon in self.game_state.bench_pokemon.items():
                if (
                    bench_pokemon is not None  # Check if slot is occupied
                    and card["info"]["evolves_from"].lower()
                    == bench_pokemon["name"].lower()
                ):
                    return True
        return False

    def evolve_pokemon(self, card, start_x):
        # First check if we can evolve any bench pokemon
        for slot_idx, bench_pokemon in self.game_state.bench_pokemon.items():
            if (
                bench_pokemon is not None  # Check if slot is occupied
                and card["info"].get("evolves_from")
                and card["info"]["evolves_from"].lower()
                == bench_pokemon["name"].lower()
            ):
                self.log_callback(
                    f"Evolving bench {bench_pokemon['name']} to {card['name']}..."
                )
                bench_position = bench_positions[slot_idx]

                def play_action():
                    self.drag(
                        (start_x, self.card_y), (bench_position[0], bench_position[1])
                    )

                if self.verify_card_play(card, start_x, play_action):
                    self.game_state.bench_pokemon[slot_idx] = {
                        "name": card["name"],
                        "info": card["info"],
                        "energies": bench_pokemon.get("energies", 0),
                    }
                    time.sleep(1)
                    return True
                else:
                    self.log_callback(
                        f"Failed to evolve bench pokemon to {card['name']}"
                    )
                    self.game_state.failed_cards.append(card)
                    return False

        # If no bench pokemon to evolve, try active pokemon
        if self.game_state.active_pokemon:  # Check if there's an active pokemon
            self.log_callback(
                f"Evolving {self.game_state.active_pokemon[0]['name']} to {card['name']}..."
            )

            def play_action():
                self.drag((start_x, self.card_y), (self.center_x, self.center_y))

            if self.verify_card_play(card, start_x, play_action):
                self.game_state.active_pokemon[0] = {
                    "name": card["name"],
                    "info": card["info"],
                    "energies": self.game_state.active_pokemon[0].get("energies", 0),
                }
                time.sleep(1)
                return True
            else:
                self.log_callback(f"Failed to evolve to {card['name']}")
                self.game_state.failed_cards.append(card)
                return False

        return False

    def add_energy_to_pokemon(self):
        if not self.running:
            return
        self.drag((750, 1450), (self.center_x, self.center_y), 0.3)

    def try_attack(self):
        self.add_energy_to_pokemon()
        self.drag((500, 1250), (self.center_x, self.center_y))
        time.sleep(0.25)
        self.reset_view()
        self.click(self.center_x, self.center_y)
        time.sleep(1)
        self.click(540, 1250)
        self.click(540, 1150)
        self.click(540, 1050)
        time.sleep(1)
        self.click(570, 1070)
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
        self.click(0, 1350, include_debug=False)
        self.click(0, 1350, include_debug=False)

    def click_bench_pokemons(self):
        if not self.running:
            return
        self.log_callback("Checking bench slots...")
        for slot_idx, bench_position in enumerate(bench_positions):
            self.click(bench_position[0], bench_position[1])
            zoomed_card_image = self.battle_controller.get_card(
                bench_position[0], bench_position[1], 1.25
            )
            pokemon_id = self.card_recognition_service.identify_card(zoomed_card_image)
            if pokemon_id:
                card_info = self.card_recognition_service.deck_info.get(
                    pokemon_id, default_pokemon_stats
                )
                # Update bench pokemon info
                current_energies = (self.game_state.bench_pokemon[slot_idx] or {}).get(
                    "energies", 0
                )
                self.game_state.bench_pokemon[slot_idx] = {
                    "name": card_info["name"].capitalize(),
                    "info": card_info,
                    "energies": current_energies,
                }
                self.log_callback(f"Bench Pokemon {slot_idx}: {card_info['name']}")
            else:
                self.game_state.bench_pokemon[slot_idx] = None
            self.reset_view()

    def check_active_pokemon(self):
        self.drag((500, 1100), (self.center_x, self.center_y))
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

    def click(self, x, y, include_debug=True):
        """Wrapper for click_position with default debug parameters"""
        if include_debug:
            click_position(
                x, y, debug_window=self.debug_window, screenshot=self.last_screenshot
            )
        else:
            click_position(x, y)

    def drag(self, start_pos, end_pos, duration=0.5):
        """Wrapper for drag_position with default debug parameters"""
        drag_position(
            start_pos,
            end_pos,
            duration,
            debug_window=self.debug_window,
            screenshot=self.last_screenshot,
        )
