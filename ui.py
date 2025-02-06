import os
import threading
import keyboard
from PIL import ImageGrab
from datetime import datetime
import customtkinter as ctk
from telegram_uploader import TelegramScreenshotUploader
from config_manager import load_config, save_config
import logging
import telebot

class DraggableApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Photel")
        self.geometry("400x450")  # Increased height to accommodate the new text box
        ctk.set_appearance_mode("dark")
        self.bind("<ButtonPress-1>", self.start_drag)
        self.bind("<B1-Motion>", self.on_drag)

        # Initialize attributes
        self.is_new_user = not os.path.exists("config.json")  # Check if config file exists
        self.input_index = 0  # Ensure input_index is always initialized
        self.api_token = None
        self.channel_id = None
        self.save_path = None
        self.screenshot_uploader = None

        # Define prompts for new users
        self.prompts = [
            "Enter your Telegram API Token:",
            "Enter your channel ID:",
            "Enter the file path:",
            "Set a password for encryption:"
        ]

        # Initialize UI
        self.initialize_ui()

    def initialize_ui(self):
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(padx=20, pady=20, fill="both", expand=True)
        self.label = ctk.CTkLabel(self.frame, text="", wraplength=380)
        self.label.pack(pady=5)
        self.entry = ctk.CTkEntry(self.frame, width=300)
        self.entry.pack(pady=5)

        # Dynamically set the button command based on user type
        if self.is_new_user:
            self.button = ctk.CTkButton(self.frame, text="Submit", command=self.handle_input)
        else:
            self.button = ctk.CTkButton(self.frame, text="Submit", command=self.verify_password)
        self.button.pack(pady=5)

        self.status_label = ctk.CTkLabel(self.frame, text="", wraplength=380)
        self.status_label.pack(pady=5)

        # Caption input box for screenshots
        self.caption_label = ctk.CTkLabel(self.frame, text="Enter caption (optional):", wraplength=380)
        self.caption_label.pack(pady=5)
        self.caption_entry = ctk.CTkEntry(self.frame, width=300)
        self.caption_entry.pack(pady=5)

        # Text box for sending messages
        self.message_label = ctk.CTkLabel(self.frame, text="Type your message here:", wraplength=380)
        self.message_label.pack(pady=5)
        self.message_textbox = ctk.CTkTextbox(self.frame, width=300, height=100)
        self.message_textbox.pack(pady=5)
        self.message_textbox.bind("<Control-Return>", self.send_message)  # Bind Ctrl+Enter to send_message

        if self.is_new_user:
            self.setup_new_user()
        else:
            self.setup_password_prompt()

    def setup_new_user(self):
        self.label.configure(text=self.prompts[0])
        self.entry.configure(show='')
        self.input_index = 0  # Reset input_index for new users

    def setup_password_prompt(self):
        self.label.configure(text="Enter your password:")
        self.entry.configure(show='*')
        self.entry.bind("<Return>", lambda event: self.verify_password())  # Bind Enter key to verify_password

    def verify_password(self, event=None):
        password = self.entry.get().strip()
        self.entry.delete(0, ctk.END)
        try:
            # Load the configuration using the provided password
            config = load_config(password)
            self.api_token = config["api_token"]
            self.channel_id = config["channel_id"]
            self.save_path = config["save_path"]

            # Log the fetched data for debugging
            logging.info(f"Fetched API Token: {self.api_token}")
            logging.info(f"Fetched Channel ID: {self.channel_id}")
            logging.info(f"Fetched Save Path: {self.save_path}")

            # Validate the API token
            bot = telebot.TeleBot(self.api_token)
            bot.get_me()  # This will raise an exception if the API token is invalid

            # Transition to capture mode
            self.show_capture_instruction()
        except Exception as e:
            # Display an error message if the password is invalid or loading fails
            self.status_label.configure(text="Invalid password or configuration", text_color="red")
            logging.error(f"Error verifying password: {e}")

    def handle_input(self, event=None):
        if not self.is_new_user:
            # Prevent input handling for returning users
            return

        current_input = self.entry.get().strip()
        self.entry.delete(0, ctk.END)

        # Assign inputs based on input_index
        if self.input_index == 0:
            self.api_token = current_input
            logging.info(f"API Token entered: {self.api_token}")
        elif self.input_index == 1:
            self.channel_id = current_input
            logging.info(f"Channel ID entered: {self.channel_id}")
        elif self.input_index == 2:
            self.save_path = current_input
            logging.info(f"Save Path entered: {self.save_path}")
        elif self.input_index == 3:
            # Validate inputs before saving
            if not self.api_token or not self.channel_id or not self.save_path:
                self.status_label.configure(text="All fields are required", text_color="red")
                return

            # Save the configuration with the provided password
            save_config(self.api_token, self.channel_id, self.save_path, current_input)
            self.show_capture_instruction()
            return

        # Increment input_index and update UI
        self.input_index += 1
        if self.input_index < len(self.prompts):
            show_asterisk = self.input_index == 3  # Show asterisks for password input
            self.entry.configure(show='*' if show_asterisk else '')
            self.label.configure(text=self.prompts[self.input_index])
        else:
            self.show_capture_instruction()

    def show_capture_instruction(self):
        if not os.path.isdir(self.save_path):
            self.status_label.configure(text="Invalid path. Exiting program.", text_color="red")
            return
        try:
            # Log the data being used for debugging
            logging.info(f"Using API Token: {self.api_token}")
            logging.info(f"Using Channel ID: {self.channel_id}")
            logging.info(f"Using Save Path: {self.save_path}")

            # Initialize Telegram bot
            bot = telebot.TeleBot(self.api_token)

            # Test the bot connection
            bot.get_me()  # This will raise an exception if the API token is invalid

            # Set up unsent directory
            unsent_directory = os.path.join(self.save_path, 'unsent')
            os.makedirs(unsent_directory, exist_ok=True)

            # Initialize screenshot uploader
            self.screenshot_uploader = TelegramScreenshotUploader(bot, self.channel_id)
            self.screenshot_uploader.set_unsent_directory(unsent_directory)

            # Start background threads
            threading.Thread(target=self.screen_capture, args=(self.save_path,), daemon=True).start()
            threading.Thread(target=bot.polling, kwargs={"none_stop": True}, daemon=True).start()

            # Update UI
            self.label.pack_forget()
            self.entry.pack_forget()
            self.button.pack_forget()
            self.status_label.configure(text="Shortcut for taking pics is SHIFT + `", text_color="green")
            self.background_button = ctk.CTkButton(self.frame, text="Go to Background", command=self.hide_ctk)
            self.background_button.pack(pady=5)
            keyboard.add_hotkey("ctrl + ]", self.restore_ctk)

        except Exception as e:
            logging.error(f"Error initializing screenshot uploader: {e}")
            self.status_label.configure(text=f"Initialization Error: {e}", text_color="red")

    def screen_capture(self, path):
        keyboard.add_hotkey("shift + `", lambda: self.capture_and_save_screen(path))
        keyboard.wait("esc")

    def capture_and_save_screen(self, path):
        screenshot = ImageGrab.grab()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        filename = f"screenshot_{timestamp}.png"
        save_path = os.path.join(path, filename)
        screenshot.save(save_path)
        logging.info(f"Screenshot saved: {save_path}")

        # Get caption from the caption input box
        caption = self.caption_entry.get().strip()
        # self.caption_entry.delete(0, ctk.END)  # Clear the caption box after use

        if hasattr(self, 'screenshot_uploader') and self.screenshot_uploader:
            self.screenshot_uploader.enqueue_screenshot(save_path, caption=caption)
            self.status_label.configure(text=f"Screenshot queued: {filename}", text_color="green")
        else:
            logging.error("Screenshot uploader not initialized")
            self.status_label.configure(text="Screenshot uploader not ready", text_color="red")

    def send_message(self, event=None):
        """
        Send the message typed in the text box to the Telegram channel.
        """
        try:
            # Get the message from the text box
            message = self.message_textbox.get("1.0", "end").strip()
            if not message:
                self.status_label.configure(text="Message cannot be empty", text_color="red")
                return

            # Initialize Telegram bot
            bot = telebot.TeleBot(self.api_token)

            # Send the message
            bot.send_message(chat_id=self.channel_id, text=message)
            logging.info(f"Message sent to channel: {message}")

            # Clear the text box
            self.message_textbox.delete("1.0", "end")
            self.status_label.configure(text="Message sent successfully!", text_color="green")
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            self.status_label.configure(text=f"Failed to send message: {e}", text_color="red")

    def start_drag(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.win_x = self.winfo_x()
        self.win_y = self.winfo_y()

    def on_drag(self, event):
        delta_x = event.x_root - self.start_x
        delta_y = event.y_root - self.start_y
        new_x = self.win_x + delta_x
        new_y = self.win_y + delta_y
        self.geometry(f"+{new_x}+{new_y}")

    def hide_ctk(self):
        self.withdraw()

    def restore_ctk(self):
        self.deiconify()