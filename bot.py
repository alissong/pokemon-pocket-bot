import os
import subprocess
import threading
import time
import uuid

import cv2
import numpy as np
import requests

from adb_utils import (
    click_position,
    connect_to_emulator,
    drag_position,
    take_screenshot,
)
from battle_actions import BattleActions
from card_data_manager import CardDataManager
from constants import bench_positions, card_offset_mapping, default_pokemon_stats
from deck import deck_info, save_deck
from image_utils import ImageProcessor
from loaders import load_all_cards, load_template_images


class PokemonBot:
    def __init__(self, app_state, log_callback, ui_instance):
        self.app_state = app_state
        self.log_callback = log_callback
        self.running = False
        self.template_images = load_template_images("images")
        # create images/cards folder if not exists
        images_cards_folder = "images/cards"
        if not os.path.exists(images_cards_folder):
            os.makedirs(images_cards_folder)
        self.card_images = load_all_cards(images_cards_folder)
        self.deck_info = deck_info
        self.card_data_manager = CardDataManager()
        self.ui_instance = ui_instance

        ## COORDS
        self.zoom_card_region = (80, 255, 740, 1020)
        self.turn_check_region = (50, 1560, 200, 20)
        self.center_x = 400
        self.center_y = 900
        self.card_start_x = 500
        self.card_y = 1500
        self.number_of_cards_region = (790, 1325, 60, 50)

        ## STATE
        self.hand_state = []
        self.active_pokemon = []
        self.bench_pokemon = []
        self.number_of_cards = None

        self.image_processor = ImageProcessor(self.log_callback)
        self.battle_actions = BattleActions(
            self.image_processor,
            self.template_images,
            self.card_images,
            self.zoom_card_region,
            self.number_of_cards_region,
            self.log_callback,
        )

    def start(self):
        if not self.app_state.program_path:
            self.log_callback("Please select emulator path first.")
            return
        self.running = True
        threading.Thread(target=self.connect_and_run).start()

    def stop(self):
        self.running = False

    def get_emulator_name(self):
        try:
            result = subprocess.run(
                ["adb", "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            output = result.stdout

            lines = output.splitlines()

            devices = [line.split("\t")[0] for line in lines[1:] if "device" in line]

            if devices:
                return devices[0]
            else:
                return None
        except Exception as e:
            print(f"Error getting emulator name: {e}")
            return None

    def connect_and_run(self):
        if self.app_state.emulator_name:
            connect_to_emulator(self.app_state.emulator_name)
        else:
            emulator_name = self.get_emulator_name()
            connect_to_emulator(emulator_name)
        self.log_callback("Connected to emulator")
        self.run_script()

    def run_script(self):
        while self.running:
            self.active_pokemon = []
            self.bench_pokemon = []
            screenshot = take_screenshot()

            ### GO THROUGH MENUS TO FIND A BATTLE
            if not self.image_processor.check_and_click(
                screenshot,
                self.template_images["BATTLE_ALREADY_SCREEN"],
                "Battle already screen",
            ):
                self.image_processor.check_and_click(
                    screenshot, self.template_images["BATTLE_SCREEN"], "Battle screen"
                )
            time.sleep(4)
            self.battle_actions.perform_search_battle_actions(
                self.running, self.stop, run_event=True
            )

            ### BATTLE START
            self.image_processor.check_and_click_until_found(
                self.template_images["TIME_LIMIT_INDICATOR"],
                "Time limit indicator",
                self.running,
                self.stop,
            )
            screenshot = take_screenshot()

            while not self.game_ended(screenshot) and not self.next_step_available(
                screenshot
            ):
                ## Case got a pokemon defeated or sabrina card
                self.click_bench_pokemons()

                self.check_active_pokemon()
                self.reset_view()
                if self.image_processor.check(
                    screenshot, self.template_images["GOING_FIRST_INDICATOR"], None
                ) or self.image_processor.check(
                    screenshot, self.template_images["GOING_SECOND_INDICATOR"], None
                ):
                    self.check_n_cards()
                    self.reset_view()
                    if self.number_of_cards:
                        self.log_callback(
                            f"Number of cards on the first turn: {self.number_of_cards}"
                        )
                        self.check_cards(True)
                        self.log_callback("Hand state on first turn:")
                        for card in self.hand_state:
                            self.log_callback(f"{card['name']}")
                        self.play_turn(is_first_turn=True)
                        self.end_turn()
                    time.sleep(1)

                elif (
                    self.battle_actions.check_turn(self.turn_check_region, self.running)
                    and self.active_pokemon
                ):
                    self.update_field_and_hand_cards()
                    self.reset_view()
                    if self.number_of_cards and self.battle_actions.check_turn(
                        self.turn_check_region, self.running
                    ):
                        self.play_turn(is_first_turn=False)
                        self.try_attack()
                        self.end_turn()
                    time.sleep(1)

                screenshot = take_screenshot()

            ### GO TO MAIN SCREEN
            time.sleep(4)
            if self.image_processor.check_and_click(
                screenshot, self.template_images["TAP_TO_PROCEED_BUTTON"], "Game ended"
            ):
                time.sleep(2)

            # click_position(self.center_x, self.center_y)

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

    def play_turn(self, is_first_turn=False):
        if not self.running:
            return False
        self.log_callback("Start playing my turn...")

        if not is_first_turn:
            self.add_energy_to_pokemon()

        ## Check playable cards (main field or bench is empty)
        if 0 < len(self.hand_state) < 8:
            self.log_callback("Hand state:")
            for card in self.hand_state:
                self.log_callback(f"{card['name']}")
                self.log_callback(f"{card['info'].get('item_card')}")
                start_x = self.card_start_x - (
                    card["position"] * card_offset_mapping.get(self.number_of_cards, 20)
                )
                self.log_callback(f"Checking card in play turn: {card}")

            card_offset_x = card_offset_mapping.get(self.number_of_cards, 20)
            for card in self.hand_state:
                ## Skip trainer cards on first turn
                if is_first_turn and card["info"].get("item_card"):
                    self.log_callback(
                        f"Skipping trainer card {card['name']} on first turn"
                    )
                    continue

                ## Check if i can play a trainer card (not on first turn)
                if not is_first_turn and card["info"].get("item_card"):
                    start_x = self.card_start_x - (card["position"] * card_offset_x)
                    self.log_callback(f"Playing trainer card: {card['name']}...")
                    drag_position(
                        (start_x, self.card_y), (self.center_x, self.center_y)
                    )
                    time.sleep(1)
                    drag_position((500, 1250), (self.center_x, self.center_y))
                    break

                if not self.running:
                    return False
                self.log_callback(f"Hand cards: {self.hand_state}")

                start_x = self.card_start_x - (card["position"] * card_offset_x)
                if card["info"].get("item_card"):
                    self.log_callback(f"🔹 Playing Trainer Card: **{card['name']}**")
                    drag_position(
                        (start_x, self.card_y), (self.center_x, self.center_y)
                    )

                if (
                    not self.active_pokemon
                    and card["info"]["level"] == 0
                    and not card["info"]["item_card"]
                ):
                    self.log_callback(f"🆕 Setting Active Pokémon: **{card['name']}**")
                    self.reset_view()
                    time.sleep(0.5)
                    drag_position(
                        (start_x, self.card_y), (self.center_x, self.center_y)
                    )
                    self.active_pokemon.append(card)
                    time.sleep(1)
                    self.log_callback("⚔️ **Battle Start!**")
                    time.sleep(1)
                elif len(self.bench_pokemon) < 3:
                    if (
                        card["info"]["level"] == 0
                        and not card["info"]["item_card"]
                        and card["name"]
                    ):
                        for bench_position in bench_positions:
                            self.reset_view()
                            time.sleep(1)
                            self.log_callback(
                                f"Playing card from position {card['position']+1} to bench {bench_position}..."
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
                        self.bench_pokemon.append(bench_pokemon_info)
                        break

                ## Check if i can evolve the main pokemon
                elif card["info"].get("evolves_from") and self.active_pokemon:
                    if (
                        card["info"]["evolves_from"].lower()
                        == self.active_pokemon[0]["name"].lower()
                    ):
                        start_x = self.card_start_x - (card["position"] * card_offset_x)

                        self.log_callback(
                            f"Evolving {self.active_pokemon[0]['name']} to {card['name']}..."
                        )
                        drag_position(
                            (start_x, self.card_y), (self.center_x, self.center_y)
                        )

                        self.active_pokemon[0] = {
                            "name": card["name"],
                            "info": card["info"],
                            "energies": self.active_pokemon[0].get("energies", 0),
                        }
                        time.sleep(1)
                        break
                time.sleep(1)
                if self.image_processor.check_and_click(
                    take_screenshot(),
                    self.template_images["START_BATTLE_BUTTON"],
                    "Start battle button",
                ):
                    time.sleep(1)
                self.reset_view()
        else:
            self.reset_view()
            self.add_energy_to_pokemon()
            self.try_attack()

    def add_energy_to_pokemon(self):
        if not self.running:
            return False
        drag_position((750, 1450), (self.center_x, self.center_y), 0.3)

    def convert_api_card_data(self, card_data):
        # Convert stage to level
        stage = card_data.get("stage", "Basic")
        level_mapping = {"Basic": 0, "Stage 1": 1, "Stage 2": 2}

        # Calculate min energy requirement from attacks
        min_energies = 0  # Default to 0
        if card_data.get("attack") is None:
            card_data["attack"] = []

        if card_data["attack"]:  # Only calculate if there are attacks
            min_energies = float("inf")
            for attack in card_data["attack"]:
                info = attack.get("info", "")
                # Count energy symbols between curly braces
                if "{" in info and "}" in info:
                    energy_text = info[info.find("{") + 1 : info.find("}")]
                    energy_count = len(
                        energy_text
                    )  # Each character represents one energy
                    min_energies = min(min_energies, energy_count)

            # If we still have infinity, it means no valid energy counts were found
            if min_energies == float("inf"):
                min_energies = 0

        return {
            "level": level_mapping.get(stage, 0),
            "energies": min_energies,
            "evolves_from": card_data.get("prew_stage_name", None),
            "can_evolve": False,  # Will be updated when scanning deck
            "item_card": card_data.get("type", "").lower() in ["item", "supporter"]
            or card_data.get("stage", "").lower() in ["item", "supporter"],
            "id": card_data.get("id", None),
            "name": card_data.get("name", None),
            "number": card_data.get("number", None),
            "set_code": card_data.get("set_code", None),
            "set_name": card_data.get("set_name", None),
            "rarity": card_data.get("rarity", None),
            "color": card_data.get("color", None),
            "type": card_data.get("type", None),
            "slug": card_data.get("slug", None),
        }

    def check_cards(self, debug_images=False):
        if not self.running:
            return False
        self.log_callback("Start checking hand cards...")
        x = self.card_start_x
        hand_cards = []
        self.hand_state.clear()

        for i in range(self.number_of_cards):
            if not self.running:
                break
            self.reset_view()

            zoomed_card_image = self.battle_actions.get_card(x, self.card_y, 1.5)
            if debug_images:
                debug_images_folder = "debug_images"
                if not os.path.exists(debug_images_folder):
                    os.makedirs(debug_images_folder)
                unique_id = str(uuid.uuid4())
                cv2.imwrite(f"{debug_images_folder}/{unique_id}.png", zoomed_card_image)

            card_name = self.battle_actions.identify_card(zoomed_card_image)
            selected_card_id = None
            selected_card = None
            if card_name is None:
                # Unknown card, prompt user
                event = threading.Event()
                error_message = (
                    None
                    if not card_name
                    else f"No cards found with name '{card_name}'. Please try again."
                )
                self.ui_instance.request_card_name(zoomed_card_image, event)

                # Wait for user input with timeout (10 seconds)
                if not event.wait(timeout=10):
                    self.log_callback("Card identification timed out or was cancelled")
                    continue

                card_name = self.ui_instance.card_name
                if not card_name:  # User cancelled or timeout occurred
                    self.log_callback("Card identification was cancelled")
                    continue

                # Fetch card info from API
                while True:
                    cards = self.card_data_manager.get_card_by_name(card_name)
                    if len(cards) == 0:
                        # Show error and retry
                        event = threading.Event()
                        self.ui_instance.request_card_name(
                            zoomed_card_image,
                            event,
                            error_message=f"No cards found with name '{card_name}'. Please try again.",
                        )
                        event.wait()
                        if not self.ui_instance.card_name:
                            break
                        card_name = self.ui_instance.card_name
                        continue

                    elif len(cards) == 1:
                        selected_card = cards[0]
                        break

                    else:
                        # Compare images to find best match
                        similarities = []
                        for card in cards:
                            image_url = self.card_data_manager.get_card_image_url(
                                card["id"]
                            )
                            response = requests.get(image_url)
                            image_data = np.asarray(
                                bytearray(response.content), dtype=np.uint8
                            )
                            api_card_image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

                            # Resize images to standard size
                            standard_size = (200, 300)
                            resized_api_card_image = cv2.resize(
                                api_card_image, standard_size
                            )
                            resized_full_card_image = cv2.resize(
                                zoomed_card_image, standard_size
                            )

                            similarity = self.image_processor.calculate_similarity(
                                resized_api_card_image, resized_full_card_image
                            )
                            similarities.append((card, similarity))

                        similarities.sort(key=lambda x: x[1], reverse=True)
                        selected_card = similarities[0][0]
                        self.log_callback(
                            f"Highest similarity is {similarities[0][1]:.2f}"
                        )

                        # Show options to user
                        event = threading.Event()
                        self.ui_instance.show_card_options(
                            similarities, zoomed_card_image, event
                        )
                        event.wait()
                        selected_card = self.ui_instance.selected_card
                        break
                selected_card_id = (
                    selected_card["id"]
                    if selected_card is not None and "id" in selected_card
                    else None
                )
                self.log_callback(f"Selected card: {selected_card}")
                # Convert API data to our format
                card_info = self.convert_api_card_data(selected_card)

                # Update deck info with converted data
                card_name = selected_card["name"].lower()
                self.deck_info[selected_card["id"]] = card_info
                self.card_images[selected_card["id"]] = zoomed_card_image
                # write to the images/cards folder
                cv2.imwrite(
                    f"images/cards/{selected_card['id']}.png", zoomed_card_image
                )
                # Update all can_evolve flags
                for key, value in self.deck_info.items():
                    # Check if current card can evolve from any existing cards
                    if (
                        value.get("evolves_from") is not None
                        and value.get("evolves_from", "").lower() == card_name.lower()
                    ):
                        self.deck_info[key]["can_evolve"] = True

                    # Check if any existing cards can evolve from current card
                    if (
                        card_info.get("evolves_from") is not None
                        and card_info.get("evolves_from", "").lower()
                        == value.get("name", "").lower()
                    ):
                        card_info["can_evolve"] = True

                save_deck(self.deck_info)

            hand_cards.append(card_name.capitalize() if card_name else "Unknown Card")
            ## TODO: manage better id and name
            use_to_search = selected_card_id if selected_card_id else card_name
            card_info = self.deck_info.get(use_to_search, None)
            if card_info is None:
                self.log_callback(
                    f"Card {card_name} not found in deck, getting from api..."
                )
                # get from the api the card info
                card = self.card_data_manager.get_card_by_id(card_name)
                if not card:
                    card = self.card_data_manager.get_card_by_name(card_name)
                if card:
                    card_info = self.convert_api_card_data(card)
                    # Update deck info with the new card
                    self.deck_info[card_name] = card_info
                    save_deck(self.deck_info)
                    self.log_callback(f"Card {card_name} found in api, added to deck")
                else:
                    card_info = (
                        default_pokemon_stats  # Fallback to default stats if not found
                    )
                    self.log_callback(
                        f"Card {card_name} not found in api, added default stats"
                    )

            card_info_with_position = {
                "name": card_name,
                "info": card_info,
                "position": i,
            }
            self.hand_state.append(card_info_with_position)

            x -= card_offset_mapping.get(self.number_of_cards, 20)

        self.log_callback(f"Your hand contains: {', '.join(hand_cards)}")

        for card in self.hand_state:
            card_name = card["name"]
            card_info = card["info"]
            position = card["position"]

            # Log detailed information for each card with position
            self.log_callback(f"- Position {position}: {card_name}")

    def click_bench_pokemons(self):
        screenshot = take_screenshot()
        if (
            not self.running
            or self.image_processor.check(
                screenshot, self.template_images["TAP_TO_PROCEED_BUTTON"], None
            )
            or self.image_processor.check(
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
        ):
            return False

        self.log_callback("Click bench slots...")
        for bench_position in bench_positions:
            click_position(bench_position[0], bench_position[1])

    def check_field(self):
        if not self.running:
            return False
        self.log_callback("Checking the field...")

        self.check_active_pokemon()
        self.reset_view()
        self.bench_pokemon = []
        for index, bench_position in enumerate(bench_positions):
            zoomed_card_image = self.battle_actions.get_card(
                bench_position[0], bench_position[1], 1.5
            )
            bench_zone_pokemon_name = self.battle_actions.identify_card(
                zoomed_card_image
            )
            if bench_zone_pokemon_name:
                card_info = self.deck_info.get(
                    bench_zone_pokemon_name, default_pokemon_stats
                )
                card_info = {
                    "name": bench_zone_pokemon_name,
                    "info": card_info,
                    "position": index,
                    "energies": 0,
                }
                self.bench_pokemon.append(card_info)
            self.reset_view()
            time.sleep(0.25)

        if self.active_pokemon:
            active = self.active_pokemon[0]
            active_info = active["info"]
            self.log_callback(f"Active Pokémon: | {active['name']} |")
        else:
            self.log_callback("No active Pokémon in play.")

        # Log bench Pokémon details
        self.log_callback("Bench Pokémon:")
        for idx, pokemon in enumerate(self.bench_pokemon, start=1):
            info = pokemon["info"]
            self.log_callback(f"| Bench Slot {idx}: {pokemon['name']} |")

    def check_active_pokemon(self):
        drag_position((500, 1100), (self.center_x, self.center_y))
        zoomed_card_image = self.battle_actions.get_card(
            self.center_x, self.center_y, 1.25
        )
        main_zone_pokemon_name = self.battle_actions.identify_card(zoomed_card_image)
        if main_zone_pokemon_name:
            self.active_pokemon = []
            card_info = self.deck_info.get(
                main_zone_pokemon_name, default_pokemon_stats
            )
            card_info = {
                "name": main_zone_pokemon_name,
                "info": card_info,
                "energies": 0,
            }
            self.active_pokemon.append(card_info)
            self.log_callback(f"Active Pokémon: {main_zone_pokemon_name}")
        else:
            self.active_pokemon = []

    def reset_view(self):
        click_position(0, 1350)
        click_position(0, 1350)

    def check_n_cards(self):
        if not self.running:
            return False
        self.number_of_cards = None
        n_cards = self.battle_actions.check_number_of_cards(500, 1500)
        if n_cards:
            self.number_of_cards = int(n_cards)

    def update_field_and_hand_cards(self):
        if not self.running:
            return False
        self.try_attack()
        self.reset_view()
        self.check_n_cards()
        self.reset_view()
        if self.number_of_cards:
            self.check_cards(True)
            # self.check_field()

    def end_turn(self):
        if not self.running:
            return False
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

    def try_attack(self):
        self.add_energy_to_pokemon()

        # Flip a coin action
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
        click_position(570, 1070)
        click_position(570, 1070)
        self.reset_view()

    def game_ended(self, screenshot):
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

    def capture_region(self, region):
        cv2.imwrite(
            "screenshot_region.png", self.image_processor.capture_region(region)
        )
