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

logger = logging.getLogger(__name__)

class DraggableApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Photel")
        self.geometry("400x450")
        ctk.set_appearance_mode("dark")
        self.bind("<ButtonPress-1>", self.start_drag)
        self.bind("<B1-Motion>", self.on_drag)

        self.is_new_user = not os.path.exists("config.json")
        self.input_index = 0
        self.api_token = None
        self.channel_id = None
        self.save_path = None
        self.screenshot_uploader = None

        self.prompts = [
            "Enter your Telegram API Token:",
            "Enter your channel ID (e.g., -1001234567890):",
            "Enter the file path for saving screenshots:",
            "Set a password for encryption:"
        ]

        self.initialize_ui()
        logger.info("DraggableApp initialized.")

    def initialize_ui(self):
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(padx=20, pady=20, fill="both", expand=True)
        self.label = ctk.CTkLabel(self.frame, text="", wraplength=380)
        self.label.pack(pady=5)
        self.entry = ctk.CTkEntry(self.frame, width=300)
        self.entry.pack(pady=5)

        self.button = ctk.CTkButton(
            self.frame,
            text="Submit",
            command=self.handle_input if self.is_new_user else self.verify_password
        )
        self.button.pack(pady=5)

        self.status_label = ctk.CTkLabel(self.frame, text="", wraplength=380)
        self.status_label.pack(pady=5)

        self.caption_label = ctk.CTkLabel(self.frame, text="Enter caption (optional):", wraplength=380)
        self.caption_label.pack(pady=5)
        self.caption_entry = ctk.CTkEntry(self.frame, width=300)
        self.caption_entry.pack(pady=5)

        self.message_label = ctk.CTkLabel(self.frame, text="Type your message here:", wraplength=380)
        self.message_label.pack(pady=5)
        self.message_textbox = ctk.CTkTextbox(self.frame, width=300, height=100)
        self.message_textbox.pack(pady=5)
        self.message_textbox.bind("<Control-Return>", self.send_message)

        if self.is_new_user:
            self.setup_new_user()
        else:
            self.setup_password_prompt()

    def setup_new_user(self):
        self.label.configure(text=self.prompts[0])
        self.entry.configure(show='')
        self.input_index = 0
        logger.info("Setting up UI for new user.")

    def setup_password_prompt(self):
        self.label.configure(text="Enter your password:")
        self.entry.configure(show='*')
        self.entry.bind("<Return>", lambda event: self.verify_password())
        logger.info("Setting up password prompt for existing user.")

    def verify_password(self, event=None):
        password = self.entry.get().strip()
        self.entry.delete(0, ctk.END)
        try:
            config = load_config(password)
            self.api_token = config["api_token"]
            self.channel_id = config["channel_id"]
            self.save_path = config["save_path"]

            logger.info(f"Fetched API Token: {self.api_token}")
            logger.info(f"Fetched Channel ID: {self.channel_id}")
            logger.info(f"Fetched Save Path: {self.save_path}")

            bot = telebot.TeleBot(self.api_token)
            bot.get_me()  # Validate API token

            self.show_capture_instruction()
        except ValueError as e:
            self.status_label.configure(text=str(e), text_color="red")
            logger.error(f"Password verification failed: {e}")
        except Exception as e:
            self.status_label.configure(text="Invalid configuration", text_color="red")
            logger.error(f"Error verifying password: {e}")

    def handle_input(self, event=None):
        if not self.is_new_user:
            return

        current_input = self.entry.get().strip()
        self.entry.delete(0, ctk.END)

        if self.input_index == 0:
            self.api_token = current_input
            logger.info(f"API Token entered: {self.api_token}")
        elif self.input_index == 1:
            self.channel_id = current_input
            logger.info(f"Channel ID entered: {self.channel_id}")
        elif self.input_index == 2:
            self.save_path = current_input
            logger.info(f"Save Path entered: {self.save_path}")
        elif self.input_index == 3:
            if not all([self.api_token, self.channel_id, self.save_path]):
                self.status_label.configure(text="All fields are required", text_color="red")
                logger.warning("Configuration save attempted with missing fields.")
                return
            try:
                save_config(self.api_token, self.channel_id, self.save_path, current_input)
                self.show_capture_instruction()
            except RuntimeError as e:
                self.status_label.configure(text=str(e), text_color="red")
                return

        self.input_index += 1
        if self.input_index < len(self.prompts):
            show_asterisk = self.input_index == 3
            self.entry.configure(show='*' if show_asterisk else '')
            self.label.configure(text=self.prompts[self.input_index])

    def show_capture_instruction(self):
        if not os.path.isdir(self.save_path):
            self.status_label.configure(text="Invalid save path provided.", text_color="red")
            logger.error(f"Invalid save path: {self.save_path}")
            return
        try:
            logger.info(f"Using API Token: {self.api_token}")
            logger.info(f"Using Channel ID: {self.channel_id}")
            logger.info(f"Using Save Path: {self.save_path}")

            bot = telebot.TeleBot(self.api_token)
            bot.get_me()  # Validate API token

            unsent_directory = os.path.join(self.save_path, 'unsent')
            os.makedirs(unsent_directory, exist_ok=True)

            self.screenshot_uploader = TelegramScreenshotUploader(bot, self.channel_id)
            self.screenshot_uploader.set_unsent_directory(unsent_directory)

            threading.Thread(
                target=self.screen_capture,
                args=(self.save_path,),
                daemon=True,
                name="ScreenCapture"
            ).start()
            threading.Thread(
                target=bot.polling,
                kwargs={"non_stop": True},
                daemon=True,
                name="TelegramPolling"
            ).start()

            self.label.pack_forget()
            self.entry.pack_forget()
            self.button.pack_forget()
            self.status_label.configure(
                text="Press Shift + ` to take a screenshot\nCtrl + ] to restore window",
                text_color="green"
            )
            self.background_button = ctk.CTkButton(self.frame, text="Go to Background", command=self.hide_ctk)
            self.background_button.pack(pady=5)
            keyboard.add_hotkey("ctrl + ]", self.restore_ctk)

            logger.info("Capture instructions displayed successfully.")

        except telebot.apihelper.ApiException as e:
            self.status_label.configure(text=f"Invalid API token or channel ID: {e}", text_color="red")
            logger.error(f"Telegram API error: {e}")
        except Exception as e:
            self.status_label.configure(text=f"Setup failed: {e}", text_color="red")
            logger.error(f"Error initializing screenshot uploader: {e}")

    def screen_capture(self, path: str):
        keyboard.add_hotkey("shift + `", lambda: self.capture_and_save_screen(path))
        keyboard.wait("esc")
        logger.info("Screen capture thread started.")

    def capture_and_save_screen(self, path: str):
        try:
            screenshot = ImageGrab.grab()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
            filename = f"screenshot_{timestamp}.png"
            save_path = os.path.join(path, filename)
            screenshot.save(save_path)
            logger.info(f"Screenshot saved: {save_path}")

            caption = self.caption_entry.get().strip()

            if self.screenshot_uploader:
                self.screenshot_uploader.enqueue_screenshot(save_path, caption=caption)
                self.status_label.configure(text=f"Screenshot queued: {filename}", text_color="green")
            else:
                logger.error("Screenshot uploader not initialized.")
                self.status_label.configure(text="Screenshot uploader not ready", text_color="red")
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            self.status_label.configure(text=f"Failed to capture screenshot: {e}", text_color="red")

    def send_message(self, event=None):
        try:
            message = self.message_textbox.get("1.0", "end").strip()
            if not message:
                self.status_label.configure(text="Message cannot be empty", text_color="red")
                return

            bot = telebot.TeleBot(self.api_token)
            bot.send_message(chat_id=self.channel_id, text=message)
            logger.info(f"Message sent to channel: {message}")

            self.message_textbox.delete("1.0", "end")
            self.status_label.configure(text="Message sent successfully!", text_color="green")
        except telebot.apihelper.ApiException as e:
            logger.error(f"Telegram API error sending message: {e}")
            self.status_label.configure(text=f"Failed to send message: {e}", text_color="red")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
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
        logger.info("Application minimized to background.")

    def restore_ctk(self):
        self.deiconify()
        logger.info("Application restored from background.")
