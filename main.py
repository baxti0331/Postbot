#!/usr/bin/env python3
"""
Telegram Bot для постинга сообщений в каналы/группы с возможностью планирования
"""

import logging
from bot import TelegramBot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    try:
        # Создаем и запускаем бота
        bot = TelegramBot()
        bot.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    main()
