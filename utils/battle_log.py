import time

import cv2

from utils.adb_utils import click_position, take_screenshot
from utils.image_utils import ImageProcessor

BATTLE_LOG_TEXT_REGION = (225, 1153, 441, 58)
BATTLE_LOG_CARD_POSITION = (133, 1181)
ZOOM_CARD_REGION = (80, 255, 740, 1020)
BATTLE_LOG_BUTTON_POSITION = (90, 1330)
BATTLE_LOG_CLOSE_POSITION = (9, 1577)


class BattleLog:
    def __init__(self, log_callback, card_recognition_service=None, debug_window=None):
        self.log_callback = log_callback
        self.debug_window = debug_window
        self.image_processor = ImageProcessor(log_callback, debug_window)
        self.card_recognition_service = card_recognition_service
        self.last_screenshot = None

        # Load template images
        self.bl_discarded = cv2.imread("images/bl_discarded.PNG")
        self.bl_put_on_bench = cv2.imread("images/bl_put_on_bench.PNG")
        self.bl_put_on_active = cv2.imread("images/bl_put_on_active.PNG")

    def identify_battle_log_card(self):
        """
        Identifies the card shown in the battle log by clicking and checking the zoomed view.
        Returns: tuple (card_id, card_info) or (None, None) if no card is identified
        """
        # Click the card position in battle log
        click_position(BATTLE_LOG_CARD_POSITION[0], BATTLE_LOG_CARD_POSITION[1])
        time.sleep(0.4)  # Wait for zoom animation

        # Capture the zoomed card region
        screenshot = take_screenshot()
        if screenshot is None:
            self.log_callback("Failed to take screenshot in identify_battle_log_card")
            return None, None

        zoomed_card = screenshot[
            ZOOM_CARD_REGION[1] : ZOOM_CARD_REGION[1] + ZOOM_CARD_REGION[3],
            ZOOM_CARD_REGION[0] : ZOOM_CARD_REGION[0] + ZOOM_CARD_REGION[2],
        ]

        # Reset view to close zoom
        self.image_processor.reset_view()

        # If card recognition service is available, identify the card
        if self.card_recognition_service:
            card_id = self.card_recognition_service.identify_card(zoomed_card)
            if card_id:
                card_info = self.card_recognition_service.deck_info.get(card_id)
                self.log_callback(
                    f"Battle log card identified: {card_info.get('name', 'Unknown')}"
                )
                return card_id, card_info

        return None, None

    def check_battle_log_action(self):
        """
        Checks the battle log region for specific actions and identifies the card if present.
        Returns: tuple (action, card_info) where action is 'discarded', 'bench', or None
        """
        self.open_battle_log()
        action = self._check_action()
        if action:
            card_id, card_info = self.identify_battle_log_card()
            self.close_battle_log()
            return action, {card_id: card_info}
        self.close_battle_log()
        return None, None

    def _check_action(self):
        """
        Internal method to check the battle log text for specific actions.
        Returns: str - 'discarded', 'bench', or None if no match found
        """
        # Original action detection code moved here
        screenshot = take_screenshot()
        if screenshot is None:
            self.log_callback("Failed to take screenshot in check_battle_log_action")
            return None

        battle_log_region = screenshot[
            BATTLE_LOG_TEXT_REGION[1] : BATTLE_LOG_TEXT_REGION[1]
            + BATTLE_LOG_TEXT_REGION[3],
            BATTLE_LOG_TEXT_REGION[0] : BATTLE_LOG_TEXT_REGION[0]
            + BATTLE_LOG_TEXT_REGION[2],
        ]

        bench_similarity = self.image_processor.calculate_similarity(
            battle_log_region, self.bl_put_on_bench
        )
        if bench_similarity > 0.8:
            self.log_callback(
                f"Battle log: Put on bench detected ({bench_similarity:.2f})"
            )
            return "bench"

        discard_similarity = self.image_processor.calculate_similarity(
            battle_log_region, self.bl_discarded
        )
        if discard_similarity > 0.8:
            self.log_callback(
                f"Battle log: Discard detected ({discard_similarity:.2f})"
            )
            return "discarded"

        active_similarity = self.image_processor.calculate_similarity(
            battle_log_region, self.bl_put_on_active
        )
        if active_similarity > 0.8:
            self.log_callback(
                f"Battle log: Put on active detected ({active_similarity:.2f})"
            )
            return "active"

        return None

    def open_battle_log(self):
        """Opens the battle log by clicking twice on the battle log button"""
        click_position(
            BATTLE_LOG_BUTTON_POSITION[0],
            BATTLE_LOG_BUTTON_POSITION[1],
            debug_window=self.debug_window,
            screenshot=self.last_screenshot,
        )
        time.sleep(0.2)
        click_position(
            BATTLE_LOG_BUTTON_POSITION[0],
            BATTLE_LOG_BUTTON_POSITION[1],
            debug_window=self.debug_window,
            screenshot=self.last_screenshot,
        )
        time.sleep(0.8)  # Wait for animation

    def close_battle_log(self):
        """Closes the battle log by clicking twice on the close button"""
        click_position(
            BATTLE_LOG_CLOSE_POSITION[0],
            BATTLE_LOG_CLOSE_POSITION[1],
            debug_window=self.debug_window,
            screenshot=self.last_screenshot,
        )
        time.sleep(0.2)
        click_position(
            BATTLE_LOG_CLOSE_POSITION[0],
            BATTLE_LOG_CLOSE_POSITION[1],
            debug_window=self.debug_window,
            screenshot=self.last_screenshot,
        )
        time.sleep(0.3)  # Wait for animation
