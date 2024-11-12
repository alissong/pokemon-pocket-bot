import time

from utils.adb_utils import long_press_position, take_screenshot
from utils.constants import NUMBER_OF_CARDS_REGION, ZOOM_CARD_REGION


class BattleController:
    def __init__(self, image_processor, template_images, card_images, log_callback):
        self.log_callback = log_callback
        self.image_processor = image_processor
        self.template_images = template_images
        self.card_images = card_images

    def check_turn(self, turn_check_region, running):
        is_your_turn = False
        self.log_callback("Checking turn...")
        if not running:
            return is_your_turn
        screenshot1 = self.image_processor.capture_region(turn_check_region)
        time.sleep(1)
        screenshot2 = self.image_processor.capture_region(turn_check_region)

        similarity = self.image_processor.calculate_similarity(screenshot1, screenshot2)
        if similarity < 0.95:
            self.log_callback("It's your turn! Taking action...")
            is_your_turn = True
        else:
            screenshot = take_screenshot()
            if (
                self.image_processor.check_and_click(
                    screenshot,
                    self.template_images.get("START_BATTLE_BUTTON"),
                    "Start battle button",
                )
                or self.image_processor.check(
                    screenshot,
                    self.template_images.get("GOING_FIRST_INDICATOR"),
                    "Going first log",
                    0.7,
                )
                or self.image_processor.check(
                    screenshot,
                    self.template_images.get("GOING_SECOND_INDICATOR"),
                    "Going second log",
                    0.7,
                )
            ):
                self.log_callback("First turn")
                is_your_turn = True
            else:
                self.log_callback("Waiting for opponent's turn...")

        return is_your_turn

    def perform_search_battle_actions(self, running, stop, run_event=False):
        if not self.image_processor.check_and_click_until_found(
            self.template_images.get("VERSUS_SCREEN"),
            "Versus Screen",
            running,
            stop,
            max_attempts=10,
        ):
            return False
        if run_event:
            if not self.image_processor.check_and_click_until_found(
                self.template_images.get("EVENT_MATCH_SCREEN"),
                "Event Match Screen",
                running,
                stop,
                max_attempts=10,
            ):
                if not self.image_processor.check_and_click_until_found(
                    self.template_images.get("RANDOM_MATCH_SCREEN"),
                    "Random Match Screen",
                    running,
                    stop,
                    max_attempts=10,
                ):
                    return False
        else:
            if not self.image_processor.check_and_click_until_found(
                self.template_images.get("RANDOM_MATCH_SCREEN"),
                "Random Match Screen",
                running,
                stop,
                max_attempts=10,
            ):
                return False
        if not self.image_processor.check_and_click_until_found(
            self.template_images.get("BATTLE_BUTTON"),
            "Battle Button",
            running,
            stop,
            max_attempts=10,
        ):
            return False

    def check_rival_concede(self, screenshot, running, stop):
        self.log_callback("Checking if the rival conceded...")
        if self.image_processor.check(
            screenshot,
            self.template_images.get("TAP_TO_PROCEED_BUTTON"),
            "Rival conceded",
        ):
            for key in [
                "NEXT_BUTTON",
                "THANKS_BUTTON",
            ]:
                if not self.image_processor.check_and_click_until_found(
                    self.template_images.get(key),
                    f"{key.replace('_', ' ').title()}",
                    running,
                    stop,
                ):
                    break
            time.sleep(2)
            self.image_processor.check_and_click_until_found(
                self.template_images.get("CROSS_BUTTON"), "Cross button", running, stop
            )
            time.sleep(4)
        else:
            self.log_callback("Rival hasn't conceded")

    def get_card(self, x, y, duration=1.0):
        x_zoom_card_region, y_zoom_card_region, w, h = ZOOM_CARD_REGION
        return long_press_position(x, y, duration)[
            y_zoom_card_region : y_zoom_card_region + h,
            x_zoom_card_region : x_zoom_card_region + w,
        ]

    def check_number_of_cards(self, card_x, card_y):
        self.log_callback("Checking the number of cards...")
        long_press_position(card_x, card_y, 1.5)

        number_image = self.image_processor.capture_region(NUMBER_OF_CARDS_REGION)

        number = self.image_processor.extract_number_from_image(number_image)
        self.log_callback(f"Number of cards: {number}")

        return number
