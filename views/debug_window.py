import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageDraw, ImageTk

# Window Configuration
DEFAULT_IMAGE_SIZE = (800, 600)
SCREEN_WIDTH_RATIO = 0.3  # 40% of screen width
SCREEN_HEIGHT_RATIO = 0.9  # 80% of screen height
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

# Add to existing constants
TIME_FORMAT = "%H:%M:%S.%f"
BUTTON_PADDING = (5, 2)


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
        self.is_open = False
        self.initial_layout_done = False
        self.start_time = time.time()
        self.filter_text = ""
        self.action_listbox = None
        self.selected_indices = set()

    def open_window(self, main_x=None, main_y=None, main_height=None):
        if self.window is not None:
            self.window.deiconify()
            self.is_open = True
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("Debug Window")
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
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

        # Add controls frame at the top
        controls_frame = tk.Frame(main_frame, bg=THEME["bg_color"])
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add history size control
        tk.Label(
            controls_frame,
            text="Max History:",
            bg=THEME["bg_color"],
            fg=THEME["fg_color"],
            font=THEME["font"],
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.history_var = tk.StringVar(value=str(self.max_history))
        history_entry = tk.Entry(
            controls_frame,
            textvariable=self.history_var,
            width=5,
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            font=THEME["font"],
        )
        history_entry.pack(side=tk.LEFT, padx=(0, 5))

        # Add apply button
        tk.Button(
            controls_frame,
            text="Apply",
            command=self._apply_history_size,
            bg=THEME["button_bg"],
            fg=THEME["fg_color"],
            font=THEME["font"],
        ).pack(side=tk.LEFT)

        # Add auto-follow toggle
        self.auto_follow_var = tk.BooleanVar(value=self.auto_follow)
        tk.Checkbutton(
            controls_frame,
            text="Auto-follow",
            variable=self.auto_follow_var,
            command=self._toggle_auto_follow,
            bg=THEME["bg_color"],
            fg=THEME["fg_color"],
            selectcolor=THEME["button_bg"],
            font=THEME["font"],
        ).pack(side=tk.RIGHT)

        # Add filter frame below controls
        filter_frame = tk.Frame(main_frame, bg=THEME["bg_color"])
        filter_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Add filter entry
        tk.Label(
            filter_frame,
            text="Filter:",
            bg=THEME["bg_color"],
            fg=THEME["fg_color"],
            font=THEME["font"],
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", self._apply_filter)
        filter_entry = tk.Entry(
            filter_frame,
            textvariable=self.filter_var,
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            font=THEME["font"],
        )
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Add import/export buttons
        buttons_frame = tk.Frame(filter_frame, bg=THEME["bg_color"])
        buttons_frame.pack(side=tk.RIGHT)

        for btn_text, cmd in [
            ("Clear", self._clear_history),
            ("Import", self._import_history),
        ]:
            tk.Button(
                buttons_frame,
                text=btn_text,
                command=cmd,
                bg=THEME["button_bg"],
                fg=THEME["fg_color"],
                font=THEME["font"],
            ).pack(side=tk.LEFT, padx=2)
        self.export_button = tk.Button(
            buttons_frame,
            text="Export",
            command=self._export_history,
            bg=THEME["button_bg"],
            fg=THEME["fg_color"],
            font=THEME["font"],
        )
        self.export_button.pack(side=tk.LEFT, padx=2)

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
            selectmode=tk.EXTENDED,
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
        self.action_listbox.bind("<<ListboxSelect>>", self._on_selection_change)

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

        # Initialize correct image size after window creation
        self.image_size = (
            max(self.image_frame.winfo_width() - WINDOW_PADDING, 1),
            max(self.image_frame.winfo_height() - WINDOW_PADDING, 1),
        )

        # After window creation, schedule a layout update
        self.window.update_idletasks()
        self.window.after(100, self._complete_initial_layout)

        self.is_open = True

    def _complete_initial_layout(self):
        """Ensure correct initial layout and image sizing"""
        if not self.initial_layout_done:
            self.initial_layout_done = True
            # Force a resize event to set correct image size
            self.on_window_resize(type("Event", (), {"widget": self.window})())
            # Refresh current image if one is selected
            if self.current_index is not None:
                self.on_action_select(None)

    def _apply_history_size(self):
        """Apply the new history size from the entry field"""
        try:
            new_size = int(self.history_var.get())
            if new_size > 0:
                self.set_max_history(new_size)
            else:
                self.history_var.set(str(self.max_history))
        except ValueError:
            self.history_var.set(str(self.max_history))

    def _toggle_auto_follow(self):
        """Toggle auto-follow based on checkbox"""
        self.auto_follow = self.auto_follow_var.get()
        if self.auto_follow:
            # Select and show the last item
            last_index = self.action_listbox.size() - 1
            if last_index >= 0:
                self.action_listbox.select_clear(0, tk.END)
                self.action_listbox.select_set(last_index)
                self.action_listbox.see(last_index)
                self.selected_indices = {last_index}
                self.on_action_select(None)
                self._update_export_button()

    def close_window(self):
        if self.window is not None:
            self.window.withdraw()
            self.is_open = False

    def _format_action_display(self, timestamp, description):
        """Format the action display with timestamp"""
        elapsed = timestamp - self.start_time
        return f"[{elapsed:.3f}s] {description}"

    def _apply_filter(self, *args):
        """Apply filter to the action list"""
        self.filter_text = self.filter_var.get().lower()
        self.refresh_action_list()

    def refresh_action_list(self):
        """Refresh the action list with current filter"""
        self.action_listbox.delete(0, tk.END)
        self.selected_indices.clear()
        for timestamp, description, _, _ in self.actions:
            if self.filter_text in description.lower():
                display_text = self._format_action_display(timestamp, description)
                self.action_listbox.insert(tk.END, display_text)
        self._update_export_button()

    def _clear_history(self):
        """Clear all history after confirmation"""
        if messagebox.askyesno(
            "Clear History", "Are you sure you want to clear all history?"
        ):
            self.actions = []
            self.images = []
            self.current_index = None
            self.refresh_action_list()
            self.image_label.configure(image="")

    def _export_history(self):
        """Export selected history items to JSON file with images"""
        selected = list(self.selected_indices)
        if not selected:
            messagebox.showwarning("Export", "No actions selected for export")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".zip", filetypes=[("ZIP files", "*.zip")]
        )
        if not filename:
            return

        try:
            import zipfile

            with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                export_data = []
                visible_actions = [
                    (i, action)
                    for i, action in enumerate(self.actions)
                    if self.filter_text in action[1].lower()
                ]

                for list_index in selected:
                    actual_index, (timestamp, description, image, coords) = (
                        visible_actions[list_index]
                    )

                    action_data = {
                        "timestamp": timestamp - self.start_time,
                        "description": description,
                        "coords": coords,
                        "has_image": image is not None,
                    }

                    if image is not None:
                        # Save image as PNG in the ZIP
                        img_filename = f"image_{actual_index}.png"
                        success, img_data = cv2.imencode(".png", image)
                        if success:
                            zipf.writestr(img_filename, img_data.tobytes())
                            action_data["image_filename"] = img_filename

                    export_data.append(action_data)

                # Save action data as JSON
                zipf.writestr("actions.json", json.dumps(export_data, indent=2))

            messagebox.showinfo(
                "Export", f"Successfully exported {len(selected)} actions"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e!s}")

    def _import_history(self):
        """Import history from ZIP file including images"""
        filename = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not filename:
            return

        try:
            import zipfile

            import numpy as np

            with zipfile.ZipFile(filename, "r") as zipf:
                # Read actions data
                actions_data = json.loads(zipf.read("actions.json"))

                # Clear existing history if needed
                if messagebox.askyesno(
                    "Import", "Clear existing history before import?"
                ):
                    self._clear_history()

                # Import actions and images
                current_time = time.time()
                for entry in actions_data:
                    timestamp = current_time + entry["timestamp"]
                    image = None

                    if entry.get("has_image") and "image_filename" in entry:
                        # Read and decode image
                        img_data = zipf.read(entry["image_filename"])
                        img_array = np.frombuffer(img_data, np.uint8)
                        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                    self.log_action(
                        entry["description"],
                        image=image,
                        action_coords=entry["coords"],
                        timestamp=timestamp,
                    )

                messagebox.showinfo(
                    "Import", f"Successfully imported {len(actions_data)} actions"
                )
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import: {e!s}")

    def log_action(
        self, action_description, image=None, action_coords=None, timestamp=None
    ):
        """Log an action with timestamp"""
        if timestamp is None:
            timestamp = time.time()

        # Limit the history size
        if len(self.actions) >= self.max_history:
            self.actions.pop(0)
            self.images.pop(0)
            self.refresh_action_list()

        # Add new action
        self.actions.append((timestamp, action_description, image, action_coords))
        self.images.append(image)

        # Update display if passes filter
        if self.filter_text.lower() in action_description.lower():
            display_text = self._format_action_display(timestamp, action_description)
            self.action_listbox.insert(tk.END, display_text)

            # Auto-select last item if auto_follow is enabled
            if self.auto_follow:
                last_index = self.action_listbox.size() - 1
                self.action_listbox.select_clear(0, tk.END)
                self.action_listbox.select_set(last_index)
                self.action_listbox.see(last_index)
                self.selected_indices = {last_index}
                self.on_action_select(None)
                self._update_export_button()

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
        """Update to handle new action format"""
        if not self.action_listbox.curselection():
            return

        index = self.action_listbox.curselection()[0]
        # Find the actual action index based on visible items
        visible_actions = [
            (i, action)
            for i, action in enumerate(self.actions)
            if self.filter_text in action[1].lower()
        ]
        if index >= len(visible_actions):
            return

        actual_index = visible_actions[index][0]
        self.current_index = actual_index
        timestamp, description, image, action_coords = self.actions[actual_index]

        if image is not None:
            # Convert image to RGB mode if it isn't already
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

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

                if action_type in ["click", "long_press"]:  # Add long_press type
                    x, y = coords
                    x, y = x * scale_x, y * scale_y
                    r = min(new_width, new_height) * CIRCLE_SIZE_RATIO
                    # Use a different color or larger circle for long press
                    if action_type == "long_press":
                        r *= 1.5  # Make the circle 50% larger for long press
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
            self.refresh_action_list()

    def _on_selection_change(self, event):
        """Handle selection changes in the listbox"""
        self.selected_indices = set(self.action_listbox.curselection())
        if len(self.selected_indices) == 1:
            # If single selection, show the image
            self.on_action_select(None)
        self._update_export_button()

    def _update_export_button(self):
        """Update export button text with selection count"""
        count = len(self.selected_indices)
        export_text = f"Export ({count})" if count > 0 else "Export"
        self.export_button.config(text=export_text)
