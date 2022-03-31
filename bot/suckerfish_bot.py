#!/usr/bin/python3

import logging
import socket
import subprocess
import time
from typing import List

import paramiko
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
                 host_password: str,
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
        self.host_password = host_password
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

    def run_sudo_command(self, command="ls",
                         jobid="None"):
        """Executes a sudo command over a established SSH connectiom.

        Args:
            command (str, optional): The command to execute. Defaults to 'ls'.
            jobid (str, optional): The job id to use. Defaults to 'None'.

        Returns:
            tuple: (bool, stderr): (True if the command was executed, the stderr)
        """

        root_ssh_client = paramiko.SSHClient()
        root_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            root_ssh_client.connect(hostname=self.host_ip,
                                    username=self.host_username,
                                    password=self.host_password,
                                    timeout=5,
                                    pkey=self.key)
        except Exception as e:
            self.logger.error(f"SSH connection failed: {e}")
            return False

        command = "sudo -S -p '' %s" % command
        self.logger.info("Job[%s]: Executing: %s" % (jobid, command))
        stdin, stdout, stderr = root_ssh_client.exec_command(command=command)
        stdin.write(self.host_password + "\n")
        stdin.flush()
        stdoutput = [line for line in stdout]
        stderroutput = [line for line in stderr]
        for output in stdoutput:
            self.logger.info("Job[%s]: %s" % (jobid, output.strip()))
        # Check exit code.
        self.logger.debug("Job[%s]:stdout: %s" % (jobid, stdoutput))
        self.logger.debug("Job[%s]:stderror: %s" % (jobid, stderroutput))
        self.logger.info("Job[%s]:Command status: %s" % (jobid, stdout.channel.recv_exit_status()))
        if not stdout.channel.recv_exit_status():
            self.logger.info("Job[%s]: Command executed." % jobid)
            root_ssh_client.close()
            if not stdoutput:
                stdoutput = True
            return True, stdoutput
        else:
            self.logger.error("Job[%s]: Command failed." % jobid)
            for output in stderroutput:
                self.logger.error("Job[%s]: %s" % (jobid, output))
            root_ssh_client.close()
            return False, stderroutput

    def is_host_online(self) -> bool:
        """Check if the host pc is online"""
        # TODO make it work for both windows and linux
        try:
            subprocess.check_output(["ping", "-c", "1", self.host_ip])
        except:
            return False
        return True

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

            # Turn on the computer
            self.power_switch.on()
            time.sleep(1)
            self.power_switch.off()

            # Let it boot into Ubuntu
            tries = 0
            while not self.is_host_online() and tries < 20:
                time.sleep(5)
                tries += 1

            # check if the host is online
            if not self.is_host_online():
                query.edit_message_text(text=f"Could not boot Windows")

            # Connect to the host via ssh
            if self.connect_ssh():
                self.logger.info("SSH connection successful")

                # Set next boot to Windows
                if self.make_windows_next():
                    self.reset_switch_action()
                else:
                    self.logger.error("Could not make Windows next")
                    query.edit_message_text(text=f"Failed to set windows on reboot")
            else:
                self.logger.error("SSH connection failed in power_on->select_os")
                query.edit_message_text(text=f"SSH connection failed")

        elif data == 'Ubuntu':
            # Nothing to do Ubuntu is the default
            query.edit_message_text(text=f"Booting Ubuntu")
                        # Let it boot into Ubuntu
            tries = 0
            while not self.is_host_online() and tries < 20:
                time.sleep(5)
                tries += 1

            # check if the host is online
            if not self.is_host_online():
                query.edit_message_text(text=f"Could not boot Ubuntu")

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

    def make_windows_next(self) -> bool:
        """Make the windows entry the default for the next boot"""

        # Execute the bash command
        return self.reboot_into_entry(self.windows_entry_id)

    def reboot_into_entry(self, entry_id: int) -> bool:
        """Reboot into the given entry"""
        # Regen the grub env
        done, _ = self.run_sudo_command("sudo grub-editenv create")
        # set the entry id
        done, _ = self.run_sudo_command("grub-reboot " + str(entry_id))
        return done
