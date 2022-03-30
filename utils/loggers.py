import html
import json
import logging
import traceback

from telegram import ParseMode, Update
from telegram.ext import CallbackContext, Updater


class DevChatLogger:

    def __init__(self,
                 dev_chat_id: str,
                 updater: Updater,
                 chat_log_level=logging.ERROR,
                 file_log_level=logging.INFO,
                 log_file='dev_chat_log.log'):
        """
        Initialize the DevChatLogger.

        Args:
            dev_chat_id (int): The telegram chat id of the developer.
            chat_log_level (int): The minimum level of logger messages to send to the developer chat.
            terminal_log_level (int): The minimum level of logger messages to print to the terminal.
        """
        self.dev_chat_id = dev_chat_id
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=file_log_level,
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
        )
        self.logger = logging.getLogger(__name__)

        self.chat_log_level = chat_log_level

        # Use the updater to send the messages
        self.updater = updater

    def error_handler(self, update: object, context: CallbackContext) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error(msg="Exception while handling an update:", exc_info=context.error)

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages longer than the 4096 character limit.
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f'An exception was raised while handling an update\n'
            f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
            '</pre>\n\n'
            f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
            f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
            f'<pre>{html.escape(tb_string)}</pre>'
        )

        # Finally, send the message
        context.bot.send_message(chat_id=self.dev_chat_id, text=message, parse_mode=ParseMode.HTML)

    def __send_log_message(self, log_msg: str) -> None:
        self.logger.debug(log_msg)

        # use the updater to send the message to the dev chat
        self.updater.bot.send_message(chat_id=self.dev_chat_id, text=log_msg, parse_mode=ParseMode.HTML)

    # python logger wrappers to log to the dev chat
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
        if self.chat_log_level <= logging.DEBUG:
            msg = f'<b>DEBUG:</b> {msg}'
            self.__send_log_message(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)
        if self.chat_log_level <= logging.INFO:
            msg = f'<b>INFO:</b> {msg}'
            self.__send_log_message(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
        if self.chat_log_level <= logging.WARNING:
            msg = f'<b>WARNING:</b> {msg}'
            self.__send_log_message(msg)

    def critical(self, msg: str) -> None:
        self.logger.critical(msg)
        if self.chat_log_level <= logging.CRITICAL:
            msg = f'<b>CRITICAL:</b> {msg}'
            self.__send_log_message(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)
        if self.chat_log_level <= logging.ERROR:
            msg = f'<b>ERROR:</b> {msg}'
            self.__send_log_message(msg)
