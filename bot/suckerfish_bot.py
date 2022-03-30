#!/usr/bin/python3

from asyncio.windows_events import NULL
import os
import socket
import time
from typing import List, Optional
import logging

import paramiko
import yaml
from gpiozero import LED
from requests import get
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Updater)


def only_allowed_chats(func):
    """Decorator for callbacks which are only allowed to a specific user list"""
    def wrapped(self, update: Update, context: CallbackContext):
        if self.allowed_chats is None:
            return func(self, update, context)
        elif str(update.message.chat_id) in self.allowed_chats:
            return func(self, update, context)
        else:
            self.logger.info(f"User {update.message.chat_id} tried to access a restricted command")
            update.message.reply_text('Only owner allowed')
    return wrapped

class SuckerfishBot:
    """ Telegram bot class with the methods to turn on and off the pc"""

    def __init__(self,
                 bot_token: str,
                 host_ip: str,
                 host_username: str,
                 power_pin: int = 21,
                 reset_pin: int = 20,
                 windows_entry_id: int = 1,  # Second after ubuntu
                 allowed_chats: List[str] = None,
                 logger = None,):
        """Initialize the bot

        Args:
            config_file (str, optional): The config file to use. Defaults to 'config.yaml'
        """

        # Load the config
        self.bot_token = bot_token
        self.allowed_chats = allowed_chats

        # Pin wiring por the switches
        self.power_pin = power_pin
        self.reset_pin = reset_pin

        # host pc data
        self.host_ip = host_ip
        self.host_username = host_username
        self.windows_entry_id = windows_entry_id

        # Make sure to set use_context=True to use the new context based callbacks
        self.updater = Updater(self.bot_token, use_context=True)

        # Get the dispatcher to register handlers
        self.dp = self.updater.dispatcher

        # SSH client
        self.ssh_client = paramiko.SSHClient()
        self.key = paramiko.RSAKey.from_private_key_file('/home/pi/.ssh/id_rsa')
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Define the power and reset pins
        self.power_switch = LED(self.power_pin)
        self.reset_switch = LED(self.reset_pin)

        # on different commands - answer in Telegram
        self.dp.add_handler(CommandHandler("current_ip", self.current_ip))
        self.dp.add_handler(CommandHandler("power_switch", self.press_power_switch))
        self.dp.add_handler(CommandHandler("reset_switch", self.press_reset_switch))
        self.dp.add_handler(CommandHandler("get_chat_id", self.send_user_chat_id))
        self.dp.add_handler(CommandHandler("is_online", self.check_host_online))

        # queries with menus
        # Use the function name as filter for the callback.
        self.dp.add_handler(CommandHandler("force_shutdown", self.force_shutdown))
        self.dp.add_handler(CallbackQueryHandler(self.check_force_shutdown, pattern="force_shutdown_"))

        self.dp.add_handler(CommandHandler("power_on", self.power_on))
        self.dp.add_handler(CallbackQueryHandler(self.select_os, pattern="power_on_"))

        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
            self.dp.add_error_handler(self.logger.error_handler)

    def connect_ssh(self, timeout=5) -> bool:
        """Connect to the ssh server"""
        try:
            self.ssh_client.connect(self.host_ip,
                                    username=self.host_username,
                                    timeout=timeout,
                                    pkey=self.key)
            return True
        except Exception as e:
            self.logger.error(f"SSH connection failed: {e}")
            return False

    def send_command_to_host(self, command: str) -> bool:
        """Send a command to the host"""
        # connect to the host
        if not self.connect_ssh():
            return False

        # Use invoke_shell to establish an 'interactive session'
        remote_conn = self.ssh_client.invoke_shell()
        self.logger.debug("Interactive SSH session established")

        # Strip the initial router prompt
        output_open = remote_conn.recv(1000)

        # See what we have
        self.logger.debug(output_open.decode('utf-8'))
        time.sleep(3)

        # Now let's send the router a command
        remote_conn.send(command + '\n')

        # Wait for the command to complete
        time.sleep(1)

        # Print the output of the session
        output_close = remote_conn.recv(5000)
        self.logger.debug(output_close.decode('utf-8'))

        # Close the connection
        self.ssh_client.close()

        return True

    def is_host_online(self):
        """Check if the host pc is online"""
        # TODO make it work for both windows and linux
        if self.ssh_client.get_transport() is not None:
            if self.ssh_client.get_transport().is_active():
                return True
            else:
                self.logger.debug(
                    f"ssh_client.get_transport().is_active() returned False"
                    f"Trying to connect to {self.host_ip} with username {self.host_username}"
                )
                return False
        else:
            self.logger.debug(
                f"ssh_client.get_transport() is None\n"
                f"Trying to connect to {self.host_ip} with username {self.host_username}"
            )
            return False

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

    def power_switch_action(self):
        self.power_switch.on()
        time.sleep(1)
        self.power_switch.off()

    @only_allowed_chats
    def press_power_switch(self, update: Update, context: CallbackContext):
        """Short the power switch on the computer"""
        self.power_switch_action()

    def reset_switch_action(self):
        self.reset_switch.on()
        time.sleep(1)
        self.reset_switch.off()

    @only_allowed_chats
    def press_reset_switch(self, update: Update, context: CallbackContext):
        """Short the reset switch on the computer"""
        self.reset_switch_action()

    def power_switch_hold(self):
        self.power_switch.on()
        time.sleep(5)
        self.power_switch.off()

    @only_allowed_chats
    def force_shutdown(self, update: Update, context: CallbackContext) -> None:
        """ Ask the user if he wants to forcefully shutdown the computer """

        # Add tag to prevent query from being handled by the wrong callbacks
        tag = "force_shutdown_"
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=tag+"yes"),
                InlineKeyboardButton("No", callback_data=tag+"no"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            'This will abruptly shutdown the computer\n Are you sure?:',
            reply_markup=reply_markup
        )

    def check_force_shutdown(self, update: Update, context: CallbackContext) -> None:
        """ Callback for the force_shutdown button, if yes hold the powerbutton for 5 seconds """
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()

        # remove tag from callback data
        tag = "force_shutdown_"
        data = query.data.replace(tag, "")

        if data == 'yes':
            query.edit_message_text(text=f"Done")
            self.power_switch_hold()
        elif data == 'no':
            query.edit_message_text(text=f"Shutdown canceled")
        else:
            self.logger.error(f"(check_force_shutdown) Unknown callback data: {data}")

    @only_allowed_chats
    def power_on(self, update: Update, context: CallbackContext):
        """Power on the computer into the selected OS"""

        # Add tag to prevent query from being handled by the wrong callbacks
        tag = "power_on_"

        if not self.is_host_online():
            # Ask the user which OS he wants to boot
            keyboard = [
                [
                    InlineKeyboardButton("Windows", callback_data=tag+'Windows'),
                    InlineKeyboardButton("Ubuntu", callback_data=tag+'Ubuntu'),
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                'Which OS do you want to boot?',
                reply_markup=reply_markup
            )
        else:
            update.message.reply_text(
                'The host is already online, please power off first'
            )

    def select_os(self, update: Update, context: CallbackContext) -> None:
        """ Callback for the power_on button, if yes boot the selected OS """
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()

        # remove tag from callback data
        tag = "power_on_"
        data = query.data.replace(tag, "")

        if data == 'Windows':
            query.edit_message_text(text=f"Booting Windows")
            self.power_switch.on()
            time.sleep(1)
            self.power_switch.off()
            time.sleep(60)
            if self.connect_ssh():
                self.logger.info("SSH connection successful")
                self.make_windows_next()
                self.reset_switch_action()
            else:
                self.logger.error("SSH connection failed in power_on->select_os")
                query.edit_message_text(text=f"SSH connection failed")

        elif data == 'Ubuntu':
            query.edit_message_text(text=f"Booting Linux")
            self.power_switch_action()
        else:
            self.logger.error(f"(select_os) Unknown callback data: {data}")

    def check_host_online(self, update: Update, context: CallbackContext) -> None:
        """Reply if the host is online"""
        if self.is_host_online():
            update.message.reply_text(
                'The host is online'
            )
        else:
            update.message.reply_text(
                'The host is offline'
            )

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
