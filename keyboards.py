"""
Клавиатуры для бота
"""

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import Dict, List
from config import BUTTONS

class Keyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню с основными функциями"""
        keyboard = [
            [InlineKeyboardButton("📤 Отправить сообщение сейчас", callback_data="post_now")],
            [InlineKeyboardButton("⏰ Запланировать сообщение", callback_data="schedule_post")],
            [InlineKeyboardButton("➕ Добавить канал/группу", callback_data="add_channel")],
            [InlineKeyboardButton("📋 Мои каналы и группы", callback_data="list_channels")],
            [InlineKeyboardButton("⏱️ Запланированные посты", callback_data="scheduled_posts")],
            [InlineKeyboardButton("🗑 Удалить канал/группу", callback_data="remove_channel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def channel_list(channels: Dict[str, dict], action: str = "remove") -> InlineKeyboardMarkup:
        """Список каналов для выбора"""
        keyboard = []
        
        for channel_id, channel_info in channels.items():
            button_text = f"📢 {channel_info['title']}"
            callback_data = f"{action}_ch_{channel_id}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton(BUTTONS["back"], callback_data="back_to_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def scheduled_posts_list(posts: List[dict]) -> InlineKeyboardMarkup:
        """Список запланированных постов"""
        keyboard = []
        
        for post in posts:
            from datetime import datetime
            schedule_time = datetime.fromisoformat(post["schedule_time"])
            time_str = schedule_time.strftime("%d.%m.%Y %H:%M")
            
            # Обрезаем сообщение для кнопки
            message_preview = post["message"][:30] + "..." if len(post["message"]) > 30 else post["message"]
            button_text = f"⏰ {time_str} - {message_preview}"
            
            callback_data = f"scheduled_detail_{post['id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton(BUTTONS["back"], callback_data="back_to_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def scheduled_post_detail(post_id: str) -> InlineKeyboardMarkup:
        """Детали запланированного поста"""
        keyboard = [
            [InlineKeyboardButton(BUTTONS["delete"], callback_data=f"delete_scheduled_{post_id}")],
            [InlineKeyboardButton(BUTTONS["back"], callback_data="scheduled_posts")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_action(action: str, target: str) -> InlineKeyboardMarkup:
        """Подтверждение действия"""
        keyboard = [
            [InlineKeyboardButton(BUTTONS["confirm"], callback_data=f"confirm_{action}_{target}")],
            [InlineKeyboardButton(BUTTONS["cancel"], callback_data="cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def cancel_keyboard() -> InlineKeyboardMarkup:
        """Инлайн клавиатура с кнопкой отмены"""
        keyboard = [[InlineKeyboardButton(BUTTONS["cancel"], callback_data="cancel")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def remove_keyboard():
        """Удаление клавиатуры"""
        from telebot.types import ReplyKeyboardRemove
        return ReplyKeyboardRemove()
