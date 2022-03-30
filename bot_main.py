from asyncio.log import logger
import os

from bot.suckerfish_bot import SuckerfishBot
from utils.loggers import DevChatLogger
from utils.config import get_config

bot_config, log_config = get_config('config.yaml')

logger = DevChatLogger(log_config)

def main():
    """Run the bot."""

    # Set the directory of the script to the current working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Create a default instance of the bot
    bot = SuckerfishBot(bot_config, logger)

    # Start the bot
    bot.start()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start() is non-blocking and will stop the bot gracefully.
    bot.idle()

if __name__ == "__main__":
    main()
