from asyncio.log import logger
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from bot.suckerfish_bot import SuckerfishBot
from utils.loggers import DevChatLogger
from utils.config import get_config

def main():
    """Run the bot."""

    # Set the directory of the script to the current working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    bot_config, log_config = get_config('config.yaml')

    logger = DevChatLogger(
        dev_updater,
        log_config['dev_chat_id'],
        log_config['log_file'],
        log_config['chat_log_level'],
        log_config['file_log_level']
    )

    try:
        bot = SuckerfishBot(
            bot_config['bot_token'],
            bot_config['host_ip'],
            bot_config['host_username'],
            bot_config['power_pin'],
            bot_config['reset_pin'],
            bot_config['windows_entry_id'],
            bot_config['allowed_chats'],
            logger
        )

        # Start the bot
        bot.start()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start() is non-blocking and will stop the bot gracefully.
        bot.idle()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, exiting...')
    except Exception as e:
        # Create the dev chat bot
        dev_updater = Updater(token=bot_config['dev_bot_token'])
        dev_bot = dev_updater.bot

        # Send the error to the dev chat
        dev_bot.send_message(
            chat_id=log_config['dev_chat_id'],
            text=f'Error: {e}'
        )


if __name__ == "__main__":
    main()
