# src/services/card_recognition_service.py

import os
import threading
import uuid

import cv2
import requests

from utils.adb_utils import find_subimage
from utils.constants import card_offset_mapping
from utils.deck import deck_info, save_deck


class CardRecognitionService:
    def __init__(
        self,
        image_processor,
        card_data_service,
        ui_instance,
        log_callback,
        card_images,
    ):
        self.image_processor = image_processor
        self.card_data_service = card_data_service
        self.ui_instance = ui_instance
        self.log_callback = log_callback
        self.deck_info = deck_info
        self.card_images = card_images

    def check_cards(
        self, number_of_cards, card_start_x, card_y, hand_state, debug_images=False
    ):
        self.log_callback("Start checking hand cards...")
        x = card_start_x
        hand_cards = []
        hand_state.clear()

        for i in range(number_of_cards):
            self.image_processor.reset_view()
            zoomed_card_image = self.image_processor.get_card(x, card_y, 1.5)

            if debug_images:
                self.save_debug_image(zoomed_card_image)

            card_id = self.identify_card(zoomed_card_image)
            selected_card = None

            if card_id is None:
                card_id, selected_card = self.handle_unknown_card(zoomed_card_image)
                if not card_id or not selected_card:
                    x -= card_offset_mapping.get(number_of_cards, 20)
                    continue
            else:
                # Attempt to retrieve card info from deck_info or card_data_service
                selected_card = self.deck_info.get(card_id)
                if not selected_card:
                    card_data = self.card_data_service.get_card_by_id(card_id)
                    if card_data:
                        selected_card = self.convert_api_card_data(card_data)
                        # Update deck_info with the new card info
                        self.deck_info[card_id] = selected_card
                        save_deck(self.deck_info)
                    else:
                        self.log_callback(
                            f"No card data found for card ID '{card_id}'."
                        )
                        x -= card_offset_mapping.get(number_of_cards, 20)
                        continue
            cap_name = selected_card["name"].capitalize()
            hand_cards.append(cap_name)
            card_info_with_position = {
                "name": cap_name,
                "info": selected_card,
                "position": i,
            }
            hand_state.append(card_info_with_position)
            x -= card_offset_mapping.get(number_of_cards, 20)

        self.log_callback(f"Your hand contains: {', '.join(hand_cards)}")

    def identify_card(self, zoomed_card_image):
        highest_similarity = 0
        identified_card = None

        for card_file_name, template_image in self.card_images.items():
            base_card_name_id = os.path.splitext(card_file_name)[0]
            _, similarity = find_subimage(zoomed_card_image, template_image)
            if similarity > 0.7 and similarity > highest_similarity:
                highest_similarity = similarity
                identified_card = base_card_name_id

        return identified_card

    def handle_unknown_card(self, zoomed_card_image):
        event = threading.Event()
        self.ui_instance.request_card_name(zoomed_card_image, event)
        event.wait()

        card_name = self.ui_instance.card_name
        if not card_name:
            self.log_callback("Card identification was cancelled or timed out.")
            return None, None

        cards = self.card_data_service.get_card_by_name(card_name)
        if not cards:
            self.log_callback(f"No cards found with name '{card_name}'.")
            return None, None

        selected_card = self.select_card(cards, zoomed_card_image)
        if not selected_card:
            self.log_callback("No card selected.")
            return None, None

        self.update_deck_and_images(selected_card, zoomed_card_image)
        card_id = selected_card["id"]
        return card_id, selected_card

    def select_card(self, cards, zoomed_card_image):
        if len(cards) == 1:
            return cards[0]
        else:
            event = threading.Event()
            similarities = self.calculate_similarities(cards, zoomed_card_image)
            self.ui_instance.show_card_options(similarities, zoomed_card_image, event)
            event.wait()
            return self.ui_instance.selected_card

    def calculate_similarities(self, cards, zoomed_card_image):
        similarities = []
        for card in cards:
            card_id = card["id"]
            image_path = f"card_images_api_cache/{card_id}.png"
            if not os.path.exists(image_path):
                # Download and save the image
                image_url = self.card_data_service.get_card_image_url(card_id)
                response = requests.get(image_url)
                with open(image_path, "wb") as f:
                    f.write(response.content)
            # Load the image from cache
            api_card_image = cv2.imread(image_path)
            # Proceed with similarity calculation
            standard_size = (200, 300)
            resized_api_card_image = cv2.resize(api_card_image, standard_size)
            resized_full_card_image = cv2.resize(zoomed_card_image, standard_size)
            similarity = self.image_processor.calculate_similarity(
                resized_api_card_image, resized_full_card_image
            )
            similarities.append((card, similarity))
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities

    def update_deck_and_images(self, selected_card, zoomed_card_image):
        card_info = self.convert_api_card_data(selected_card)
        card_id = selected_card["id"]
        self.deck_info[card_id] = card_info
        self.card_images[card_id] = zoomed_card_image
        cv2.imwrite(f"images/cards/{card_id}.png", zoomed_card_image)
        save_deck(self.deck_info)

    def convert_api_card_data(self, card_data):
        stage = card_data.get("stage", "Basic")
        level_mapping = {"Basic": 0, "Stage 1": 1, "Stage 2": 2}
        min_energies = 0
        if card_data.get("attack"):
            min_energies = min(
                len(attack.get("cost", [])) for attack in card_data["attack"]
            )
        return {
            "level": level_mapping.get(stage, 0),
            "energies": min_energies,
            "evolves_from": card_data.get("prew_stage_name", None),
            "can_evolve": False,
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

    def save_debug_image(self, image):
        debug_images_folder = "debug_images"
        if not os.path.exists(debug_images_folder):
            os.makedirs(debug_images_folder)
        unique_id = str(uuid.uuid4())
        cv2.imwrite(f"{debug_images_folder}/{unique_id}.png", image)

    def check_specific_card(self, position, card_start_x, card_y, number_of_cards):
        """
        Check a specific card position in the hand.
        Returns (card_id, card_info) tuple if card is found, (None, None) otherwise.
        """
        self.image_processor.reset_view()

        # Calculate x position based on card position and offset
        offset = card_offset_mapping.get(number_of_cards, 20)
        x = card_start_x - (position * offset)

        # Get and analyze the card image
        zoomed_card_image = self.image_processor.get_card(x, card_y, 1.5)
        card_id = self.identify_card(zoomed_card_image)

        if card_id is None:
            return None, None

        # Get card info from deck_info or card_data_service
        selected_card = self.deck_info.get(card_id)
        if not selected_card:
            card_data = self.card_data_service.get_card_by_id(card_id)
            if card_data:
                selected_card = self.convert_api_card_data(card_data)
                # Update deck_info with the new card info
                self.deck_info[card_id] = selected_card
                save_deck(self.deck_info)
            else:
                return None, None

        return card_id, selected_card
