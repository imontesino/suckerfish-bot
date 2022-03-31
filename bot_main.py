import argparse
import os
from re import I

from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from bot.suckerfish_bot import SuckerfishBot
from utils.config import get_config
from utils.loggers import DevChatLogger


def parse_args():
    """Parses the CLI arguments."""
    parser = argparse.ArgumentParser(description='Suckerfish bot main script')

    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run the bot in interactive mode.")
    parser.add_argument("--config", "-c", type=str,
                        help="Path to the config file.")

    return parser.parse_args()


def main():
    """Run the bot."""

    args = parse_args()

    # Set the directory of the script to the current working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if args.config is None:
        config_file = 'config.yaml'
    else:
        config_file = args.config

    bot_config, log_config = get_config(config_file)

    logger = DevChatLogger(
        log_config['dev_bot_token'],
        log_config['dev_chat_id'],
        chat_log_level=log_config['chat_log_level'],
        file_log_level=log_config['file_log_level'],
        log_file=log_config['log_file']
    )

    try:
        bot = SuckerfishBot(
            bot_config['bot_token'],
            bot_config['host_ip'],
            bot_config['host_username'],
            bot_config['host_password'],
            bot_config['power_pin'],
            bot_config['reset_pin'],
            bot_config['windows_entry_id'],
            bot_config['allowed_chats'],
            logger
        )

        if args.interactive:
            import IPython
            IPython.embed()

        # Start the bot
        bot.start()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start() is non-blocking and will stop the bot gracefully.
        bot.idle()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, exiting...')
    except Exception as e:
        logger.critical(f'An error occurred in suckerbot: {e}')


if __name__ == "__main__":
    main()
