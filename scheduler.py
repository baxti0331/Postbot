"""
Планировщик сообщений
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import TelegramBot

from database import Database
from config import SCHEDULER_CHECK_INTERVAL

logger = logging.getLogger(__name__)

class MessageScheduler:
    def __init__(self, bot: 'TelegramBot'):
        self.bot = bot
        self.database = Database()
        self.running = False
        self._task = None
    
    def start(self):
        """Запуск планировщика"""
        if self.running:
            return
        
        self.running = True
        import threading
        import time
        
        def scheduler_loop():
            while self.running:
                try:
                    self._check_due_posts_sync()
                    time.sleep(SCHEDULER_CHECK_INTERVAL)
                except Exception as e:
                    logger.error(f"Ошибка в планировщике: {e}")
                    time.sleep(SCHEDULER_CHECK_INTERVAL)
        
        self._thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Планировщик сообщений запущен")
    
    def stop(self):
        """Остановка планировщика"""
        self.running = False
        logger.info("Планировщик сообщений остановлен")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                await self._check_due_posts()
                await asyncio.sleep(SCHEDULER_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(SCHEDULER_CHECK_INTERVAL)
    
    def _check_due_posts_sync(self):
        """Проверка и отправка готовых к отправке постов"""
        due_posts = self.database.get_due_posts()
        
        for post in due_posts:
            try:
                self._send_scheduled_post_sync(post)
                import asyncio
                asyncio.run(self.database.remove_scheduled_post(post["id"]))
                logger.info(f"Запланированный пост {post['id']} отправлен")
            except Exception as e:
                logger.error(f"Ошибка при отправке запланированного поста {post['id']}: {e}")
    
    def _send_scheduled_post_sync(self, post: dict):
        """Отправка запланированного поста"""
        user_id = post["user_id"]
        message = post["message"]
        channels = post["channels"]
        
        # Получаем актуальные каналы пользователя
        user_channels = self.database.get_user_channels(user_id)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for channel_id in channels:
            if channel_id not in user_channels:
                continue
            
            try:
                self.bot.bot.send_message(
                    chat_id=channel_id,
                    text=message,
                    parse_mode='HTML'
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                channel_title = user_channels.get(channel_id, {}).get('title', channel_id)
                errors.append(f"❌ {channel_title}: {str(e)}")
        
        # Уведомляем пользователя о результатах
        result_message = f"📊 Результаты отправки запланированного сообщения:\n\n"
        result_message += f"✅ Успешно отправлено: {success_count}\n"
        result_message += f"❌ Ошибок: {error_count}\n"
        
        if errors:
            result_message += f"\nОшибки:\n" + "\n".join(errors[:5])  # Показываем первые 5 ошибок
        
        try:
            self.bot.bot.send_message(
                chat_id=user_id,
                text=result_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
