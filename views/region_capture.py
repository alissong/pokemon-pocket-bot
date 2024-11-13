import tkinter as tk

import cv2
from PIL import Image, ImageTk

THEME = {
    "bg_color": "#2E3440",
    "fg_color": "#D8DEE9",
    "accent_color": "#81A1C1",
    "button_bg": "#4C566A",
    "entry_bg": "#3B4252",
    "entry_fg": "#D8DEE9",
    "font": ("Consolas", 10),
}


class RegionCaptureUI:
    def __init__(self, image):
        """
        Initialize the Region Capture window

        Args:
            image: numpy array of the screenshot (BGR format)
        """
        self.root = tk.Toplevel()
        self.root.title("Region Capture")
        self.root.configure(bg=THEME["bg_color"])

        # Convert BGR to RGB
        self.original_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.display_image = self.original_image.copy()

        # Calculate scaled dimensions while maintaining aspect ratio
        screen_width = self.root.winfo_screenwidth() * 0.8
        screen_height = self.root.winfo_screenheight() * 0.8

        height, width = self.original_image.shape[:2]
        scale = min(screen_width / width, screen_height / height)
        self.scaled_width = int(width * scale)
        self.scaled_height = int(height * scale)

        # Scale the image
        self.scaled_image = cv2.resize(
            self.display_image, (self.scaled_width, self.scaled_height)
        )

        # Create PhotoImage
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.scaled_image))

        # Create canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.scaled_width,
            height=self.scaled_height,
            bg=THEME["bg_color"],
            highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=10)

        # Display image on canvas
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        # Variables for rectangle drawing
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.selected_region = None

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Add confirm button
        self.confirm_button = tk.Button(
            self.root,
            text="Confirm Selection",
            command=self.confirm_selection,
            state=tk.DISABLED,
            font=THEME["font"],
            bg=THEME["button_bg"],
            fg=THEME["fg_color"],
            activebackground=THEME["accent_color"],
            activeforeground=THEME["fg_color"],
            relief=tk.FLAT,
            padx=15,
            pady=5,
        )
        self.confirm_button.pack(pady=10)

        self.result = None

    def on_press(self, event):
        """Handle mouse press event"""
        self.start_x = event.x
        self.start_y = event.y

        # Delete existing rectangle if any
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def on_drag(self, event):
        """Handle mouse drag event"""
        if self.rect_id:
            self.canvas.delete(self.rect_id)

        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            event.x,
            event.y,
            outline=THEME["accent_color"],  # Updated to theme color
            width=2,
        )

    def on_release(self, event):
        """Handle mouse release event"""
        if self.start_x and self.start_y:
            # Calculate the actual coordinates (accounting for scaling)
            scale_x = self.original_image.shape[1] / self.scaled_width
            scale_y = self.original_image.shape[0] / self.scaled_height

            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)

            # Convert to original image coordinates
            orig_x1 = int(x1 * scale_x)
            orig_y1 = int(y1 * scale_y)
            orig_x2 = int(x2 * scale_x)
            orig_y2 = int(y2 * scale_y)

            self.selected_region = (
                orig_x1,
                orig_y1,
                orig_x2 - orig_x1,
                orig_y2 - orig_y1,
            )
            self.confirm_button.config(state=tk.NORMAL)

    def confirm_selection(self):
        """Handle confirm button click"""
        self.result = self.selected_region
        self.root.destroy()

    def get_region(self):
        """
        Show the window and wait for result

        Returns:
            tuple: (x, y, width, height) or None if cancelled
        """
        self.root.wait_window()
        return self.result
