import logging
import sys
import os
from config import Config

level = logging.DEBUG if Config.DEBUG else logging.INFO

def get_logger(name: str = "bot"):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Консольний обробник
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Запис логів в bot.log
    log_dir = 'logs/'
    log_path = 'logs/bot.log'

    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(log_path, encoding='utf-8-sig')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
