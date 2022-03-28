#!/usr/bin/python3

import os
import socket
import time
from typing import List

import yaml
import paramiko
from gpiozero import LED
from requests import get
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Updater)

jupyter_active = False

def only_allowed(func):
    """Decorator for callbacks which are only allowed to a specific user list"""
    def wrapped(self, update: Update, context: CallbackContext):
        if self.allowed_chats is None:
            return func(self, update, context)
        elif str(update.message.chat_id) in self.allowed_chats:
            return func(update, context)
        else:
            update.message.reply_text('Only owner allowed')
    return wrapped

class SuckerfishBot:
    """ Telegram bot class with the methods to turn on and off the pc"""

    def __init__(self,
                 config_file: str = 'config.yaml'):
        """Initialize the bot

        Args:
            config_file (str, optional): The config file to use. Defaults to 'config.yaml'
        """

        # Load the config
        self.get_config(config_file)

        # SSH client
        self.ssh_client = paramiko.SSHClient()
        self.key = paramiko.RSAKey.from_private_key_file('/home/pi/.ssh/id_rsa')
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(self.host_ip, username=self.host_username)

        # Define the power and reset pins
        self.power_switch = LED(self.power_pin)
        self.reset_switch = LED(self.reset_pin)

        # Make sure to set use_context=True to use the new context based callbacks
        self.updater = Updater(self.bot_token, use_context=True)

        # Get the dispatcher to register handlers
        self.dp = self.updater.dispatcher

        # on different commands - answer in Telegram
        self.dp.add_handler(CommandHandler("current_ip", self.current_ip))
        self.dp.add_handler(CommandHandler("power_switch", self.press_power_switch))
        self.dp.add_handler(CommandHandler("reset_switch", self.press_reset_switch))
        self.dp.add_handler(CommandHandler('force_shutdown', self.force_shutdown))
        self.dp.add_handler(CommandHandler('ge_chat_id', self.send_user_chat_id))
        self.dp.add_handler(CallbackQueryHandler(self.button))

    def get_config(self, config_file: str):
        """Get the config from the yaml file"""
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

            self.bot_token: str = config['telegram_api']['bot_token']
            if self.bot_token is None or self.bot_token == '':
                raise ValueError('No bot token found in config file')

            self.allowed_chats: List[str] = config['telegram_api']['allowed_chats']

            # Pin wiring por the switches
            self.power_pin: int = config['pin_wiring']['power_pin']
            self.reset_pin: int = config['pin_wiring']['reset_pin']

            # host pc data
            self.host_ip: str = config['host_pc']['local_ip']
            self.host_username: str = config['host_pc']['username']
            self.windows_entry_id: int = config['host_pc']['grub_windows_entry']

    def start(self):
        """Start the bot."""
        self.updater.start_polling()

    def idle(self):
        """
        Run the bot until you press Ctrl-C or the process receives SIGINT,
        SIGTERM or SIGABRT. This should be used most of the time, since
        start_polling() is non-blocking and will stop the bot gracefully.
        """
        self.updater.idle()

    def echo(self, update: Update, context: CallbackContext):
        """Echo the user message. Use to test if the bot is running"""
        update.message.reply_text(update.message.text)

    def send_user_chat_id(self, update: Update, context: CallbackContext) -> int:
        """Send the chat id of the user asking for it"""
        update.message.reply_text(f"Your chat id is {update.message.chat_id}")

    def current_ip(self, update: Update, context: CallbackContext):
        """Send the current local and public ips of the pizero machine"""
        pub_ip = get('https://api.ipify.org').text
        local_ip = socket.gethostbyname(socket.getfqdn())
        message = (
        """local ip = {}\npublic ip = {}""".format(local_ip, pub_ip)
        )
        update.message.reply_text(message)

    @only_allowed
    def press_power_switch(self, update: Update, context: CallbackContext):
        """Short the power switch on the computer"""
        self.power_switch.on()
        time.sleep(1)
        self.power_switch.off()

    @only_allowed
    def press_reset_switch(self, update: Update, context: CallbackContext):
        """Short the reset switch on the computer"""
        self.reset_switch.on()
        time.sleep(1)
        self.reset_switch.off()

    @only_allowed
    def force_shutdown(self, update: Update, context: CallbackContext) -> None:
        """ Ask the user if he wants to forcefully shutdown the computer """
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data='1'),
                InlineKeyboardButton("No", callback_data='2'),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            'This will abruptly shutdown the computer\n Are you sure?:',
            reply_markup=reply_markup
        )

    def button(self, update: Update, context: CallbackContext) -> None:
        """ Callback for the force_shutdown button, if yes hold the powerbutton for 5 seconds """
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()

        if query.data == '1':
            query.edit_message_text(text=f"Done")
            self.power_switch.on()
            time.sleep(5)
            self.power_switch.off()
        else:
            query.edit_message_text(text=f"Shutdown canceled")

    def make_windows_next(self):
        """Make the windows entry the default for the next boot"""
        filename = "resources/grubenv_template"
        with open(filename, "r") as file:
            #read whole file to a string
            data = file.read()

        #replace the configured entry
        grubenv_text = data.replace("<entry_id>", str(self.windows_entry_id))

        bash_command = "sudo echo '" + grubenv_text + "' > /boot/grub/grubenv"

        # Execute the bash command
        self.ssh_client.exec_command(bash_command)


def main():
    """Run the bot."""

    # Set the directory of the script to the current working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Create a default instance of the bot
    bot = SuckerfishBot()

    # Start the bot
    bot.start()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start() is non-blocking and will stop the bot gracefully.
    bot.idle()

if __name__ == "__main__":
    main()
