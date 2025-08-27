import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(name: str = __name__) -> logging.Logger:
    # Створюємо логер
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Створюємо директорію для логів якщо її немає
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Форматування логів
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Хендлер для консолі
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Хендлер для файлу
    file_handler = RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Створюємо глобальний логер
logger = setup_logging()

# Експортуємо
__all__ = ['setup_logging', 'logger']