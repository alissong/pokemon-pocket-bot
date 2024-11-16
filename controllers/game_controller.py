# controllers/game_controller.py
import threading
import time
import traceback

from utils.adb_utils import click_position, drag_position, take_screenshot
from utils.battle_log import BattleLog
from utils.constants import bench_positions, card_offset_mapping, default_pokemon_stats

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
        self.running_event = threading.Event()  # Use threading.Event

        ## COORDS
        self.zoom_card_region = (80, 255, 740, 1020)
        self.turn_check_region = (50, 1560, 200, 20)
        self.center_x = 400
        self.center_y = 900
        self.card_start_x = 525
        self.card_y = 1470
        self.number_of_cards_region = (790, 1325, 60, 50)
        self.debug_window = debug_window
        self.last_screenshot = None

        # New flag to track turn state
        self.is_new_turn = True  # Assume starting as a new turn

        # Add battle_log initialization
        self.battle_log = BattleLog(
            log_callback, card_recognition_service, debug_window
        )

    def start(self):
        if not self.app_state.program_path:
            self.log_callback("Please select emulator path first.")
            return
        self.running_event.set()  # Set the event to indicate running
        threading.Thread(target=self.run).start()

    def stop(self):
        self.running_event.clear()  # Clear the event to stop the bot

    def run(self):
        """Main bot loop"""
        try:
            self.log_callback("🔄 Starting bot...")

            # Try to connect first
            if not self.emulator_controller.connect_and_run():
                self.log_callback("❌ Failed to connect to any device. Stopping bot.")
                self.running_event.clear()
                return

            self.log_callback("✅ Connected successfully")

            while self.running_event.is_set():
                try:
                    # Check connection status
                    devices = self.emulator_controller.get_all_devices()
                    connected = any(
                        device["id"] == self.app_state.emulator_name
                        and device["state"] == "device"
                        for device in devices
                    )

                    if not connected:
                        self.log_callback(
                            "⚠️ Lost connection to device. Attempting to reconnect..."
                        )
                        if not self.emulator_controller.connect_and_run():
                            self.log_callback("❌ Failed to reconnect. Stopping bot.")
                            self.running_event.clear()
                            return
                        self.log_callback("✅ Reconnected successfully")

                    # Normal bot operations with status updates
                    self.log_callback("🎮 Starting new battle sequence")
                    self.prepare_for_battle()
                    self.navigate_to_battle()
                    self.start_battle()
                    self.handle_battle()
                    self.end_battle()
                    self.log_callback("✅ Battle sequence completed")

                except Exception as e:
                    error_msg = f"⚠️ Error during battle sequence:\n{e!s}\n\nTraceback:\n{''.join(traceback.format_exc())}"
                    self.log_callback(error_msg)
                    time.sleep(5)  # Wait before retrying

        except Exception as e:
            error_msg = f"❌ Critical error in bot loop:\n{e!s}\n\nTraceback:\n{''.join(traceback.format_exc())}"
            self.log_callback(error_msg)
            self.running_event.clear()

    def prepare_for_battle(self):
        self.game_state.reset()

    def navigate_to_battle(self):
        if not self.running_event.is_set():
            return
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
            self.running_event, run_event=True
        )

    def start_battle(self):
        if not self.running_event.is_set():
            return
        self.image_processor.check_and_click_until_found(
            self.template_images["TIME_LIMIT_INDICATOR"],
            "Time limit indicator",
            self.running_event,
        )
        time.sleep(3)

    def handle_battle(self):
        while self.running_event.is_set():
            screenshot = take_screenshot()
            if self.is_battle_over(screenshot) or self.next_step_available(screenshot):
                break

            self.battle_controller.check_rival_afk(screenshot)
            # Add check for rival concede
            self.battle_controller.check_rival_concede(screenshot, self.running_event)

            is_turn, self.game_state.is_first_turn, self.game_state.go_first = (
                self.battle_controller.check_turn(
                    self.turn_check_region, self.running_event, self.game_state
                )
            )

            self.check_active_pokemon()
            self.reset_view()

            time.sleep(3)  # wait to draw the card if need

            if is_turn and self.game_state.active_pokemon:
                if self.is_new_turn:
                    self.update_game_state()
                    self.is_new_turn = False  # Reset the flag after updating
                self.play_turn()
                self.end_turn()
            elif is_turn:
                if self.is_new_turn:
                    self.update_game_state()
                    self.is_new_turn = False  # Reset the flag after updating
                self.process_hand_cards()
                # time.sleep(1)
                if (
                    self.game_state.is_first_turn
                    and self.image_processor.check_and_click_until_found(
                        self.template_images.get("START_BATTLE_BUTTON"),
                        "Start battle button",
                        self.running_event,
                        similarity_threshold=0.5,
                        max_attempts=10,
                    )
                ):
                    self.game_state.first_turn_done = True
                    self.is_new_turn = True
                if self.game_state.active_pokemon:
                    self.end_turn()
            else:
                self.click_bench_positions()
                self.is_new_turn = True

            if self.game_state.go_first and self.game_state.go_first_done:
                self.game_state.go_first = False
                self.log_callback("Played first!")
            else:
                self.log_callback("Waiting for opponent's turn...")
                time.sleep(1)

            # Detect new cards drawn (e.g., after end of turn)
            # if self.detect_new_cards():
            # self.update_game_state()

    def detect_new_cards(self):
        """
        Detects if new cards have been drawn by comparing the current number of cards
        with the expected number. Returns True if new cards are detected.
        """
        current_number = self.battle_controller.check_number_of_cards(500, 1500)
        if current_number and self.game_state.number_of_cards:
            if int(current_number) > self.game_state.number_of_cards:
                self.log_callback("New cards detected. Updating game state...")
                return True
        return False

    # Update methods to check self.running_event.is_set()
    def update_game_state(self, cards_delta=0):
        if not self.running_event.is_set():
            return
        self.reset_view()
        self.check_number_of_cards(cards_delta)
        self.reset_view()
        # self.check_active_pokemon()
        self.reset_view()
        if cards_delta == 0:
            if self.game_state.number_of_cards and self.game_state.number_of_cards > 0:
                self.log_callback("🔍 Scanning cards...")
                self.card_recognition_service.check_cards(
                    self.game_state.number_of_cards,
                    self.card_start_x,
                    self.card_y,
                    self.game_state.hand_state,
                    False,
                )
            else:
                self.game_state.hand_state = []

    def play_turn(self):
        if not self.running_event.is_set():
            return
        self.log_callback("🎮 Starting turn...")
        time.sleep(1)

        if not self.game_state.is_first_turn:
            self.add_energy_to_pokemon()
        self.check_active_pokemon()
        self.check_bench_cards()

        if 0 < len(self.game_state.hand_state):
            # self.log_callback("📋 Current hand:")
            # for card in self.game_state.hand_state:
            #     self.log_callback(f"  • {card['name']}")

            # self.log_callback("\n🪑 Bench status:")
            # for slot, pokemon in self.game_state.bench_pokemon.items():
            #     if pokemon:
            #         self.log_callback(
            #             f"  [{slot}] {pokemon['name']} (⚡ {pokemon['energies']})"
            #         )
            #     else:
            #         self.log_callback(f"  [{slot}] Empty")
            self.reset_view()
            self.process_hand_cards()

    def process_hand_cards(self):
        if not self.running_event.is_set():
            return

        if not self.game_state.number_of_cards:
            self.check_number_of_cards()
            if not self.game_state.number_of_cards:
                self.log_callback("⚠️ Could not determine number of cards in hand")
                return

        self.reset_view()

        # Initial scan of all cards in hand
        if len(self.game_state.hand_state) == 0:
            self.update_game_state()

        cards_played = 0
        max_cards_per_turn = 5  # Safety limit

        while cards_played < max_cards_per_turn and self.game_state.hand_state:
            cards_to_play = []
            current_hand = self.game_state.hand_state[:]
            cards_played_this_iteration = 0

            # First, identify all playable cards
            for card in current_hand:
                if card in self.game_state.failed_cards:
                    continue

                if self.game_state.is_first_turn and card["info"].get("item_card"):
                    continue

                if (
                    card["info"].get("item_card")
                    and self.game_state.played_trainer_cards >= 2
                ):
                    continue

                can_play = False
                if card["info"].get("item_card"):
                    can_play = True
                elif self.can_set_active_pokemon(card):
                    can_play = True
                elif self.can_place_on_bench(card):
                    can_play = True
                elif self.can_evolve_pokemon(card):
                    can_play = True

                if can_play:
                    cards_to_play.append(card)

            if not cards_to_play:
                break

            # Now try to play each identified card
            played_any = False
            for card in cards_to_play:
                if not self.running_event.is_set():
                    return

                card_offset_x = card_offset_mapping.get(
                    len(self.game_state.hand_state), 20
                )
                start_x = self.card_start_x - (card["position"] * card_offset_x)

                action_taken = False
                delta = 0

                # Try to play the card
                if card["info"].get("item_card"):
                    played, this_delta = self.play_trainer_card(card, start_x)
                    delta += this_delta
                    if played:
                        self.game_state.played_trainer_cards += 1
                        self.remove_card_from_hand(card)
                        action_taken = True
                elif self.can_set_active_pokemon(card):
                    if self.set_active_pokemon(card, start_x):
                        self.remove_card_from_hand(card)
                        action_taken = True
                elif self.can_place_on_bench(card):
                    if self.place_pokemon_on_bench(card, start_x):
                        self.remove_card_from_hand(card)
                        action_taken = True
                elif self.can_evolve_pokemon(card):
                    if self.evolve_pokemon(card, start_x):
                        self.remove_card_from_hand(card)
                        action_taken = True

                if action_taken:
                    played_any = True
                    cards_played += 1
                    cards_played_this_iteration += 1
                    # Update positions for remaining cards
                    for i, remaining_card in enumerate(self.game_state.hand_state):
                        remaining_card["position"] = i
                    self.reset_view()
                    time.sleep(1)

            if not played_any:
                break

            delta -= cards_played_this_iteration
            # Scan for any new cards that might have been drawn
            if self.detect_new_cards() or delta != 0:
                self.update_game_state(delta)

        # Reset counters after processing all cards
        self.game_state.played_trainer_cards = 0
        self.game_state.failed_cards = []

    def remove_card_from_hand(self, card):
        """
        Removes a card from the hand_state manually after it has been played.
        """
        try:
            self.game_state.hand_state.remove(card)
            self.log_callback(f"Removed card {card['name']} from hand manually.")
        except ValueError:
            self.log_callback(f"Card {card['name']} not found in hand to remove.")

    def verify_card_play(self, card, action_func):
        """
        Verifies if a card was successfully played by checking the battle log.

        Args:
            card: The card being played
            action_func: Function that performs the actual card play action

        Returns:
            bool: True if the card was successfully played, False otherwise
        """
        # Perform the card play action
        action_func()
        time.sleep(2)  # Wait for animation to complete
        if not self.game_state.first_turn_done:
            self.log_callback(
                "Skipping card play verification on first turn because dont have logs..."
            )
            return True
        time.sleep(2)  # Need to really wait for some animations
        # Check battle log for the action
        self.reset_view()
        action, card_info = self.battle_log.check_battle_log_action()

        if action:
            self.log_callback(f"Battle log detected action: {action}")
            # If we got card info from battle log, verify it matches our played card
            if card_info:
                played_card_id = next(
                    iter(card_info.keys())
                )  # Get the first (and only) card ID
                if played_card_id == card["info"]["id"]:
                    self.log_callback(
                        f"Verified {card['name']} was played successfully"
                    )
                    return True
                else:
                    self.log_callback(
                        f"Battle log card ID mismatch: expected {card['info']['id']}, got {played_card_id}"
                    )
            else:
                # If no card info but action detected, assume success
                self.log_callback(
                    f"Action detected but no card info, assuming {card['name']} was played successfully"
                )
                return True

        self.log_callback(f"No battle log action detected for {card['name']}")
        return False

    def play_trainer_card(self, card, start_x):
        self.log_callback(f"Playing trainer card: {card['name']}...")
        card_name_lower = card["name"].lower()

        # Define the card play action
        def play_action():
            # time.sleep(1)
            self.drag_first_y((start_x, self.card_y), (self.center_x, self.center_y))

        # Attempt to play the card and verify success
        if self.verify_card_play(card, play_action):
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
            # time.sleep(0.7)
            self.drag((start_x, self.card_y), (self.center_x, self.center_y - 50))

        if self.verify_card_play(card, play_action):
            self.game_state.active_pokemon.clear()
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
            # time.sleep(1)
            self.log_callback(
                f"Placing card {card['name']} on bench at position {empty_slot}..."
            )
            self.drag_first_y(
                (start_x, self.card_y), (bench_position[0], bench_position[1])
            )

        if self.verify_card_play(card, play_action):
            bench_pokemon_info = {
                "name": card["name"].capitalize(),
                "info": card["info"],
                "energies": 0,
            }
            self.game_state.bench_pokemon[empty_slot] = bench_pokemon_info
            self.log_callback(f"Updated bench slot {empty_slot} with {card['name']}")
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
                    self.drag_first_y(
                        (start_x, self.card_y), (bench_position[0], bench_position[1])
                    )

                if self.verify_card_play(
                    card, play_action
                ):  # TODO here start_x must come from hand position of the card
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
                self.drag_first_y(
                    (start_x, self.card_y), (self.center_x, self.center_y)
                )

            if self.verify_card_play(card, play_action):
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
        if not self.running_event.is_set():
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
        if not self.running_event.is_set():
            return
        self.try_attack()
        self.reset_view()
        time.sleep(0.35)
        screenshot = take_screenshot()
        if not self.image_processor.check_and_click(
            screenshot, self.template_images["END_TURN"], "End turn"
        ):
            self.log_callback("❌ End turn not found")
            return
        time.sleep(1.0)
        screenshot = take_screenshot()
        self.image_processor.check_and_click(
            screenshot, self.template_images["OK"], "Ok"
        )
        self.game_state.is_first_turn = False  # Ensure we reset the first turn flag
        self.game_state.go_first_done = True
        # Mark that the next turn is a new turn
        self.is_new_turn = True

    def end_battle(self):
        if not self.running_event.is_set():
            return
        time.sleep(4)
        screenshot = take_screenshot()
        if self.image_processor.check_and_click(
            screenshot, self.template_images["TAP_TO_PROCEED_BUTTON"], "Game ended"
        ):
            time.sleep(2)

        max_attempts = 5
        for _ in range(max_attempts):
            if not self.running_event.is_set():
                return
            screenshot = take_screenshot()
            if self.image_processor.check_and_click(
                screenshot,
                self.template_images["NEXT_BUTTON"],
                "Checking next button",
            ):
                time.sleep(2)
                break
            time.sleep(1)

        for _ in range(max_attempts):
            if not self.running_event.is_set():
                return
            screenshot = take_screenshot()
            if self.image_processor.check_and_click(
                screenshot,
                self.template_images["THANKS_BUTTON"],
                "Checking thanks button",
            ):
                time.sleep(3)
                break
            time.sleep(1)

        self.image_processor.check_and_click(
            screenshot,
            self.template_images["CROSS_BUTTON"],
            "Checking cross button",
        )
        time.sleep(3)

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
        if not self.running_event.is_set():
            return

        # Handle the delta case first
        if self.game_state.number_of_cards is not None and cards_delta != 0:
            self.game_state.number_of_cards += cards_delta
            self.log_callback(
                f"Adjusted number of cards by delta: {cards_delta}, new total: {self.game_state.number_of_cards}"
            )
            return

        # Reset and check for new count
        self.game_state.number_of_cards = None
        n_cards = self.battle_controller.check_number_of_cards(500, 1500)
        if n_cards:
            try:
                self.game_state.number_of_cards = int(n_cards)
                self.log_callback(
                    f"Updated number of cards: {self.game_state.number_of_cards}"
                )
            except (ValueError, TypeError):
                self.log_callback("⚠️ Failed to parse number of cards")
                self.game_state.number_of_cards = None
        else:
            self.log_callback("⚠️ Could not determine number of cards in hand")

    def reset_view(self):
        self.click(0, 1350, include_debug=False)
        self.click(0, 1350, include_debug=False)

    def check_bench_cards(self):
        """Full bench check that identifies cards and updates game state"""
        if not self.running_event.is_set():
            return
        self.log_callback("Checking bench cards...")
        for slot_idx, bench_position in enumerate(bench_positions):
            self.reset_view()
            time.sleep(0.5)
            self.click(bench_position[0], bench_position[1])
            zoomed_card_image = self.battle_controller.get_card(
                bench_position[0], bench_position[1], 0.7
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
                time.sleep(0.35)
            else:
                self.game_state.bench_pokemon[slot_idx] = None
            self.reset_view()

    def click_bench_positions(self):
        """Simply clicks all bench positions and active pokemon spot without checking cards"""
        if not self.running_event.is_set():
            return
        self.log_callback("Clicking bench positions...")
        # Click bench positions
        for bench_position in bench_positions:
            self.click(bench_position[0], bench_position[1])
            self.reset_view()
        # Click active pokemon position
        # self.click(self.center_x, self.center_y)
        self.reset_view()

    def check_active_pokemon(self):
        self.drag((500, 1100), (self.center_x, self.center_y))
        zoomed_card_image = self.battle_controller.get_card(
            self.center_x, self.center_y, 0.7
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
        # else:
        # self.game_state.active_pokemon = []

    def click(self, x, y, include_debug=True):
        """Wrapper for click_position with default debug parameters"""
        if include_debug and self.debug_window and self.debug_window.is_open:
            click_position(
                x, y, debug_window=self.debug_window, screenshot=self.last_screenshot
            )
        else:
            click_position(x, y)

    def drag(self, start_pos, end_pos, duration=0.5):
        """Wrapper for drag_position with default debug parameters"""
        if self.debug_window and self.debug_window.is_open:
            drag_position(
                start_pos,
                end_pos,
                duration,
                debug_window=self.debug_window,
                screenshot=self.last_screenshot,
            )
        else:
            drag_position(start_pos, end_pos, duration)

    def drag_first_y(self, start_pos, end_pos, duration=0.5):
        # drag_first_y(
        # start_pos, end_pos, duration, self.debug_window, self.last_screenshot
        # )
        ## TODO: Implement drag_first_y, not working as expected
        drag_position(
            start_pos, end_pos, duration, self.debug_window, self.last_screenshot
        )
