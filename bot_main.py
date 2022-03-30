from asyncio.log import logger
import os

from bot.suckerfish_bot import SuckerfishBot
from utils.loggers import DevChatLogger
from utils.config import get_config

def main():
    """Run the bot."""

    # Set the directory of the script to the current working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    bot_config, log_config = get_config('config.yaml')

    logger = DevChatLogger(
        bot_config['dev_bot_token'],
        bot_config['dev_chat_id'],
        log_config['log_file'],
        log_config['chat_log_level'],
        log_config['file_log_level']
    )

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

    # Start the bot
    bot.start()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start() is non-blocking and will stop the bot gracefully.
    bot.idle()

if __name__ == "__main__":
    main()
