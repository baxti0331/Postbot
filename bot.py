"""
Основной класс Telegram бота
"""

import logging
import telebot
import threading
import time

from config import BOT_TOKEN
from handlers import BotHandlers
from scheduler import MessageScheduler

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.handlers = BotHandlers(self.bot)
        self.scheduler = None
        self.running = False
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Команды
        @self.bot.message_handler(commands=['start'])
        def start_handler(message):
            self.handlers.start_command(message)
            
        @self.bot.message_handler(commands=['help'])
        def help_handler(message):
            self.handlers.help_command(message)
            
        @self.bot.message_handler(commands=['post'])
        def post_handler(message):
            self.handlers.post_command(message)
            
        @self.bot.message_handler(commands=['schedule'])
        def schedule_handler(message):
            self.handlers.schedule_command(message)
            
        @self.bot.message_handler(commands=['manage'])
        def manage_handler(message):
            self.handlers.manage_command(message)
        
        # Callback запросы
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            self.handlers.handle_callback(call)
        
        # Текстовые сообщения
        @self.bot.message_handler(content_types=['text'])
        def message_handler(message):
            self.handlers.handle_message(message)
        
        logger.info("Обработчики настроены")
    
    def start(self):
        """Запуск бота"""
        try:
            # Настраиваем обработчики
            self._setup_handlers()
            
            # Запускаем планировщик
            self.scheduler = MessageScheduler(self)
            scheduler_thread = threading.Thread(target=self.scheduler.start, daemon=True)
            scheduler_thread.start()
            
            # Запускаем бота
            logger.info("Запуск бота...")
            self.running = True
            
            logger.info("Бот успешно запущен и готов к работе!")
            
            # Запускаем polling с обработкой ошибок для 24/7 работы
            while self.running:
                try:
                    self.bot.polling(none_stop=True, interval=0, timeout=20)
                except Exception as e:
                    logger.error(f"Ошибка polling: {e}")
                    import time
                    time.sleep(5)  # Ждем 5 секунд перед повторной попыткой
                    if self.running:
                        logger.info("Перезапуск polling...")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
        finally:
            self.running = False
            if self.scheduler:
                self.scheduler.stop()
