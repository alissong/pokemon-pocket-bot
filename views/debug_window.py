import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

# Window Configuration
DEFAULT_IMAGE_SIZE = (800, 600)
SCREEN_WIDTH_RATIO = 0.4  # 40% of screen width
SCREEN_HEIGHT_RATIO = 0.8  # 80% of screen height
PANED_WINDOW_RATIO = 0.3  # 30% of width for action list
WINDOW_PADDING = 20  # Padding for image display

# Visual Configuration
LISTBOX_FONT = ("Helvetica", 10)
LISTBOX_SELECT_BG = "#0078D7"
LISTBOX_SELECT_FG = "white"

# Drawing Configuration
CIRCLE_SIZE_RATIO = 0.02  # Relative to window size
CLICK_MARKER_COLOR = "red"
DRAG_LINE_COLOR = "blue"
MARKER_WIDTH = 3  # Width of drawn markers

# Theme Configuration
THEME = {
    "bg_color": "#2E3440",
    "fg_color": "#D8DEE9",
    "accent_color": "#81A1C1",
    "button_bg": "#4C566A",
    "entry_bg": "#3B4252",
    "entry_fg": "#D8DEE9",
    "font": ("Consolas", 10),
}


class DebugWindow:
    def __init__(self, root, max_history=50):
        self.root = root
        self.window = None
        self.max_history = max_history
        self.actions = []
        self.images = []
        self.current_index = None
        self.image_size = DEFAULT_IMAGE_SIZE
        self.auto_follow = True

    def open_window(self, main_x=None, main_y=None, main_height=None):
        if self.window is not None:
            self.window.deiconify()
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("Debug Window")
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        self.window.configure(bg=THEME["bg_color"])

        screen_width = self.root.winfo_screenwidth()
        window_width = int(screen_width * SCREEN_WIDTH_RATIO)

        # Use main window height if provided, otherwise 80% of screen height
        if main_height:
            window_height = main_height
        else:
            window_height = int(self.root.winfo_screenheight() * SCREEN_HEIGHT_RATIO)

        self.window.geometry(f"{window_width}x{window_height}")

        # Position window to the right of main window if coordinates provided
        if main_x is not None and main_y is not None:
            main_width = self.root.winfo_width()
            self.window.geometry(f"+{main_x + main_width + 0}+{main_y}")

        # Create main frame with theme
        main_frame = tk.Frame(self.window, bg=THEME["bg_color"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Update PanedWindow style
        style = ttk.Style()
        style.configure("Custom.TPanedwindow", background=THEME["bg_color"])
        paned_window = ttk.Panedwindow(
            main_frame, orient=tk.HORIZONTAL, style="Custom.TPanedwindow"
        )
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Theme the frames
        self.action_frame = tk.Frame(paned_window, bg=THEME["bg_color"])
        self.image_frame = tk.Frame(paned_window, bg=THEME["bg_color"])

        # Add frames to paned window
        paned_window.add(self.action_frame, weight=1)
        paned_window.add(self.image_frame, weight=3)

        # Set up action list with scrollbar
        scrollbar = tk.Scrollbar(
            self.action_frame, bg=THEME["bg_color"], troughcolor=THEME["entry_bg"]
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.action_listbox = tk.Listbox(
            self.action_frame,
            font=THEME["font"],
            selectmode=tk.SINGLE,
            activestyle="dotbox",
            bg=THEME["entry_bg"],
            fg=THEME["fg_color"],
            selectbackground=THEME["accent_color"],
            selectforeground=THEME["fg_color"],
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.action_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.action_listbox.yview)

        # Bind selection event
        self.action_listbox.bind("<<ListboxSelect>>", self.on_action_select)

        # Add image resize handling
        self.window.bind("<Configure>", self.on_window_resize)

        # Image display label
        self.image_label = tk.Label(self.image_frame, bg=THEME["bg_color"])
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # Configure weights for resizing
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Set initial paned window sash position after adding panes
        self.window.update()
        paned_window.sashpos(0, int(window_width * PANED_WINDOW_RATIO))

    def close_window(self):
        if self.window is not None:
            self.window.withdraw()

    def log_action(self, action_description, image=None, action_coords=None):
        # Limit the history size
        if len(self.actions) >= self.max_history:
            self.actions.pop(0)
            self.images.pop(0)
            self.action_listbox.delete(0)

        # Add new action
        self.actions.append((action_description, image, action_coords))
        self.action_listbox.insert(tk.END, action_description)
        self.images.append(image)

        # Auto-select last item if auto_follow is enabled
        if self.auto_follow:
            last_index = self.action_listbox.size() - 1
            self.action_listbox.select_clear(0, tk.END)
            self.action_listbox.select_set(last_index)
            self.action_listbox.see(last_index)
            self.on_action_select(None)

    def on_window_resize(self, event):
        if event.widget == self.window:
            # Update image size based on frame size with minimum size protection
            frame_width = max(
                self.image_frame.winfo_width(), 100
            )  # Minimum 100px width
            frame_height = max(
                self.image_frame.winfo_height(), 100
            )  # Minimum 100px height
            self.image_size = (
                max(frame_width - WINDOW_PADDING, 1),  # Ensure at least 1px
                max(frame_height - WINDOW_PADDING, 1),  # Ensure at least 1px
            )

            # Refresh current image if one is selected
            if self.current_index is not None:
                self.on_action_select(None)

    def on_action_select(self, event):
        if not self.action_listbox.curselection():
            return

        index = self.action_listbox.curselection()[0]
        last_index = self.action_listbox.size() - 1

        # Update auto_follow based on whether the last item is selected
        self.auto_follow = index == last_index

        self.current_index = index
        action_description, image, action_coords = self.actions[index]

        if image is not None:
            pil_image = Image.fromarray(image)

            # Calculate aspect ratio preserving resize
            img_width, img_height = pil_image.size
            aspect_ratio = img_width / img_height

            target_width, target_height = self.image_size
            target_aspect = target_width / target_height

            # Ensure minimum dimensions
            if aspect_ratio > target_aspect:
                new_width = max(target_width, 1)
                new_height = max(int(target_width / aspect_ratio), 1)
            else:
                new_height = max(target_height, 1)
                new_width = max(int(target_height * aspect_ratio), 1)

            # First resize the image
            display_image = pil_image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            # Then draw on the resized image
            draw = ImageDraw.Draw(display_image)

            # Draw action overlay with correct scaling
            if action_coords:
                action_type = action_coords.get("type")
                coords = action_coords.get("coords")

                # Scale coordinates based on original to new image size ratio
                scale_x = new_width / img_width
                scale_y = new_height / img_height

                if action_type == "click":
                    x, y = coords
                    x, y = x * scale_x, y * scale_y
                    r = min(new_width, new_height) * CIRCLE_SIZE_RATIO
                    draw.ellipse(
                        (x - r, y - r, x + r, y + r),
                        outline=CLICK_MARKER_COLOR,
                        width=MARKER_WIDTH,
                    )
                elif action_type == "drag":
                    start_x, start_y, end_x, end_y = coords
                    start_x, start_y = start_x * scale_x, start_y * scale_y
                    end_x, end_y = end_x * scale_x, end_y * scale_y
                    draw.line(
                        (start_x, start_y, end_x, end_y),
                        fill=DRAG_LINE_COLOR,
                        width=MARKER_WIDTH,
                    )

            # Convert to PhotoImage and display
            tk_image = ImageTk.PhotoImage(display_image)
            self.image_label.configure(image=tk_image)
            self.image_label.image = tk_image

    def set_max_history(self, max_history):
        self.max_history = max_history
        # Trim history if necessary
        while len(self.actions) > self.max_history:
            self.actions.pop(0)
            self.images.pop(0)
            self.action_listbox.delete(0)
