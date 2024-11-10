import os

import cv2


def load_template_images(template_folder):
    template_images = {}

    if not os.path.exists(template_folder):
        print(f"Directory {template_folder} does not exist.")
        return template_images

    for filename in os.listdir(template_folder):
        if filename.endswith(".PNG"):
            file_path = os.path.join(template_folder, filename)
            image = cv2.imread(file_path)
            if image is not None:
                template_name = os.path.splitext(filename)[0].upper()
                template_images[template_name] = image
                print(f"Loaded template: {template_name}")
            else:
                print(f"Failed to load template: {file_path}")

    return template_images


def load_all_cards(image_folder):
    card_images = {}

    if not os.path.exists(image_folder):
        print(f"Directory {image_folder} does not exist.")
        return card_images

    for filename in os.listdir(image_folder):
        if filename.endswith((".png", ".jpg", ".jpeg")):
            file_path = os.path.join(image_folder, filename)
            image = cv2.imread(file_path)
            if image is not None:
                card_images[filename] = image
                print(f"Loaded image: {filename}")
            else:
                print(f"Failed to load image: {file_path}")

    return card_images
