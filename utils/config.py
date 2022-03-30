from typing import List
import yaml

from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL

str2log_level = {
    'debug': DEBUG,
    'info': INFO,
    'warning': WARNING,
    'error': ERROR,
    'critical': CRITICAL
}

def get_config(config_file: str):
    """Preps the config file for use in the bot and logger

    Args:
        config_file (str): The path to the config file.

    Raises:
        ValueError: If the config file is not found.

    Returns:
        tuple(tuple, tuple): The config file as a tuple of tuples.

    """
    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

        bot_token: str = config['telegram_api']['bot_token']
        if bot_token is None or bot_token == '':
            raise ValueError('No bot token found in config file')

        allowed_chats: List[str] = config['telegram_api']['allowed_chats']

        # Pin wiring por the switches
        power_pin: int = config['pin_wiring']['power_pin']
        reset_pin: int = config['pin_wiring']['reset_pin']

        # host pc data
        host_ip: str = config['host_pc']['local_ip']
        host_username: str = config['host_pc']['username']
        windows_entry_id: int = config['host_pc']['grub_windows_entry']

        # logging
        dev_chat_id: str = config['logging']['dev_chat_id']
        dev_bot_token: str = config['logging']['dev_bot_token']
        log_file: str = config['logging']['log_file']
        chat_log_level: int = config['logging']['chat_log_level']
        file_log_level: int = config['logging']['file_log_level']

    # bot config: bot_token, host_ip, host_username, power_pin, reset_pin, windows_entry_id, allowed_chats)
    bot_config = {
        'bot_token': bot_token,
        'host_ip': host_ip,
        'host_username': host_username,
        'power_pin': power_pin,
        'reset_pin': reset_pin,
        'windows_entry_id': windows_entry_id,
        'allowed_chats': allowed_chats
    }

    # logging config: log_file, chat_log_level, file_log_level
    log_config = {
        'dev_bot_token': dev_bot_token,
        'dev_chat_id': dev_chat_id,
        'log_file': log_file,
        'chat_log_level': str2log_level[chat_log_level.lower()],
        'file_log_level': str2log_level[file_log_level.lower()]
    }

    return bot_config, log_config
