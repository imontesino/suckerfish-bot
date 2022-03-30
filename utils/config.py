from typing import List
import yaml

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

        dev_chat_id: int = config['telegram_api']['dev_chat_id']
        allowed_chats: List[str] = config['telegram_api']['allowed_chats']

        # Pin wiring por the switches
        power_pin: int = config['pin_wiring']['power_pin']
        reset_pin: int = config['pin_wiring']['reset_pin']

        # host pc data
        host_ip: str = config['host_pc']['local_ip']
        host_username: str = config['host_pc']['username']
        windows_entry_id: int = config['host_pc']['grub_windows_entry']

        # logging
        log_file: str = config['logging']['log_file']
        chat_log_level: int = config['logging']['chat_log_level']
        file_log_level: int = config['logging']['file_log_level']

    bot_config = (bot_token, host_ip, host_username, power_pin, reset_pin, windows_entry_id, allowed_chats)
    log_config = (dev_chat_id, chat_log_level, file_log_level, log_file)

    return bot_config, log_config
