import html
import json
import logging
import traceback

from telegram import ParseMode, Update
from telegram.ext import CallbackContext


class DevChatLogger:

    def __init__(self,
                 dev_chat_id,
                 chat_log_level=logging.ERROR,
                 file_log_level=logging.INFO,
                 log_file_name='dev_chat_log.log'):
        """
        Initialize the DevChatLogger.

        Args:
            dev_chat_id (int): The telegram chat id of the developer.
            chat_log_level (int): The minimum level of logger messages to send to the developer chat.
            terminal_log_level (int): The minimum level of logger messages to print to the terminal.
        """
        self.dev_chat_id = dev_chat_id
        logging.basicConfig(
            filename=log_file_name,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=file_log_level
        )
        self.logger = logging.getLogger(__name__)

        self.chat_log_level = chat_log_level

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

    def __send_log_message(self, update: Update, msg: str) -> None:
        self.logger.debug(msg)

        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f'Log message\n'
            f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
            '</pre>\n\n'
            f'<pre>{html.escape(msg)}</pre>'
        )

        self.logger.info(message)

    # python logger wrappers to log to the dev chat
    def debug(self, update: Update, msg: str) -> None:
        self.logger.debug(msg)
        if self.chat_log_level <= logging.DEBUG:
            self.__send_log_message(update, msg)

    def info(self, update: Update, msg: str) -> None:
        self.logger.info(msg)
        if self.chat_log_level <= logging.INFO:
            self.__send_log_message(update, msg)

    def warning(self, update: Update, msg: str) -> None:
        self.logger.warning(msg)
        if self.chat_log_level <= logging.WARNING:
            self.__send_log_message(update, msg)

    def critical(self, update: Update, msg: str) -> None:
        self.logger.critical(msg)
        if self.chat_log_level <= logging.CRITICAL:
            self.__send_log_message(update, msg)

    def error(self, update: Update, msg: str) -> None:
        self.logger.error(msg)
        if self.chat_log_level <= logging.ERROR:
            self.__send_log_message(update, msg)
