"""
Обработчики команд и сообщений бота
"""

import logging
from datetime import datetime
from typing import Dict, Any
import telebot

from database import Database
from keyboards import Keyboards
from config import MESSAGES, TIME_FORMATS

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, bot):
        self.bot = bot
        self.database = Database()
        self.keyboards = Keyboards()
        
        # Состояния пользователей
        self.user_states: Dict[int, Dict[str, Any]] = {}
    
    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Получение состояния пользователя"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {"state": None, "data": {}}
        return self.user_states[user_id]
    
    def set_user_state(self, user_id: int, state: str, data: Dict[str, Any] = None):
        """Установка состояния пользователя"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {"state": None, "data": {}}
        
        self.user_states[user_id]["state"] = state
        if data:
            self.user_states[user_id]["data"].update(data)
    
    def clear_user_state(self, user_id: int):
        """Очистка состояния пользователя"""
        if user_id in self.user_states:
            self.user_states[user_id] = {"state": None, "data": {}}
    
    def start_command(self, message):
        """Обработчик команды /start"""
        self.bot.send_message(
            message.chat.id,
            MESSAGES["start"],
            reply_markup=self.keyboards.main_menu(),
            parse_mode='HTML'
        )
    
    def help_command(self, message):
        """Обработчик команды /help"""
        self.bot.send_message(
            message.chat.id,
            MESSAGES["help"],
            reply_markup=self.keyboards.main_menu(),
            parse_mode='HTML'
        )
    
    def post_command(self, message):
        """Обработчик команды /post"""
        user_id = message.from_user.id
        channels = self.database.get_user_channels(user_id)
        
        if not channels:
            self.bot.send_message(message.chat.id, MESSAGES["no_channels"])
            return
        
        self.set_user_state(user_id, "waiting_post_message")
        markup = self.keyboards.cancel_keyboard()
        self.bot.send_message(
            message.chat.id,
            MESSAGES["enter_message"],
            reply_markup=markup
        )
    
    def schedule_command(self, message):
        """Обработчик команды /schedule"""
        user_id = message.from_user.id
        channels = self.database.get_user_channels(user_id)
        
        if not channels:
            self.bot.send_message(message.chat.id, MESSAGES["no_channels"])
            return
        
        self.set_user_state(user_id, "waiting_schedule_message")
        markup = self.keyboards.cancel_keyboard()
        self.bot.send_message(
            message.chat.id,
            MESSAGES["enter_schedule_message"],
            reply_markup=markup
        )
    
    def manage_command(self, message):
        """Обработчик команды /manage"""
        self.bot.send_message(
            message.chat.id,
            "🛠 Главное меню управления ботом:",
            reply_markup=self.keyboards.main_menu()
        )
    
    def handle_message(self, message):
        """Обработчик текстовых сообщений"""
        user_id = message.from_user.id
        message_text = message.text
        user_state = self.get_user_state(user_id)
        
        # Проверка на отмену (сообщения не обрабатываются, только callback)
        if message_text == "❌ Отмена":
            self.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                MESSAGES["cancel"],
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        state = user_state.get("state")
        
        if state == "waiting_post_message":
            self._handle_post_message(message, message_text)
        elif state == "waiting_schedule_message":
            self._handle_schedule_message(message, message_text)
        elif state == "waiting_schedule_time":
            self._handle_schedule_time(message, message_text)
        elif state == "waiting_channel_id":
            self._handle_channel_id(message, message_text)
    
    def _handle_post_message(self, message_obj, message: str):
        """Обработка сообщения для немедленной отправки"""
        user_id = message_obj.from_user.id
        channels = self.database.get_user_channels(user_id)
        
        self.clear_user_state(user_id)
        
        # Отправляем сообщение во все каналы
        success_count = 0
        error_count = 0
        errors = []
        
        for channel_id, channel_info in channels.items():
            try:
                self.bot.send_message(
                    chat_id=channel_id,
                    text=message,
                    parse_mode='HTML'
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(MESSAGES["posting_error"].format(
                    title=channel_info['title'], 
                    error=str(e)
                ))
        
        # Результат отправки
        result_message = f"📊 Результаты отправки:\n\n"
        result_message += f"✅ Успешно отправлено: {success_count}\n"
        result_message += f"❌ Ошибок: {error_count}\n"
        
        if errors:
            result_message += f"\nОшибки:\n" + "\n".join(errors[:3])
        
        self.bot.send_message(
            message_obj.chat.id,
            result_message,
            reply_markup=self.keyboards.main_menu(),
            parse_mode='HTML'
        )
    
    def _handle_schedule_message(self, message_obj, message: str):
        """Обработка сообщения для планирования"""
        user_id = message_obj.from_user.id
        
        self.set_user_state(user_id, "waiting_schedule_time", {"message": message})
        self.bot.send_message(message_obj.chat.id, MESSAGES["enter_schedule_time"])
    
    def _handle_schedule_time(self, message_obj, time_str: str):
        """Обработка времени для планирования"""
        user_id = message_obj.from_user.id
        user_state = self.get_user_state(user_id)
        message = user_state["data"]["message"]
        
        # Парсинг времени
        schedule_time = None
        for time_format in TIME_FORMATS:
            try:
                schedule_time = datetime.strptime(time_str.strip(), time_format)
                break
            except ValueError:
                continue
        
        if not schedule_time:
            self.bot.send_message(message_obj.chat.id, MESSAGES["invalid_time"])
            return
        
        # Проверка, что время в будущем
        if schedule_time <= datetime.now():
            self.bot.send_message(message_obj.chat.id, MESSAGES["time_in_past"])
            return
        
        # Добавляем в планировщик
        channels = list(self.database.get_user_channels(user_id).keys())
        import asyncio
        post_id = asyncio.run(self.database.add_scheduled_post(
            user_id, message, schedule_time, channels
        ))
        
        self.clear_user_state(user_id)
        
        time_str_formatted = schedule_time.strftime("%d.%m.%Y %H:%M")
        self.bot.send_message(
            message_obj.chat.id,
            MESSAGES["message_scheduled"].format(time=time_str_formatted),
            reply_markup=self.keyboards.main_menu()
        )
    
    def _handle_channel_id(self, message_obj, channel_id: str):
        """Обработка ID канала/группы"""
        user_id = message_obj.from_user.id
        
        try:
            # Получаем информацию о чате
            chat = self.bot.get_chat(channel_id)
            
            # Проверяем права бота
            member = self.bot.get_chat_member(channel_id, self.bot.get_me().id)
            if member.status not in ['administrator', 'creator']:
                self.bot.send_message(
                    message_obj.chat.id,
                    f"❌ Бот должен быть администратором в {chat.title}"
                )
                return
            
            # Добавляем канал
            import asyncio
            success = asyncio.run(self.database.add_user_channel(
                user_id, channel_id, chat.title
            ))
            
            if success:
                self.bot.send_message(
                    message_obj.chat.id,
                    MESSAGES["channel_added"].format(title=chat.title),
                    reply_markup=self.keyboards.main_menu()
                )
            else:
                self.bot.send_message(
                    message_obj.chat.id,
                    MESSAGES["max_channels"],
                    reply_markup=self.keyboards.main_menu()
                )
            
        except Exception as e:
            self.bot.send_message(
                message_obj.chat.id,
                MESSAGES["channel_error"].format(error=str(e)),
                reply_markup=self.keyboards.main_menu()
            )
        
        self.clear_user_state(user_id)
    
    def handle_callback(self, call):
        """Обработчик callback запросов"""
        self.bot.answer_callback_query(call.id)
        
        user_id = call.from_user.id
        data = call.data
        
        if data == "post_now":
            self._handle_post_now(call, user_id)
        elif data == "schedule_post":
            self._handle_schedule_post(call, user_id)
        elif data == "add_channel":
            self._handle_add_channel(call, user_id)
        elif data == "remove_channel":
            self._handle_remove_channel(call, user_id)
        elif data == "list_channels":
            self._handle_list_channels(call, user_id)
        elif data == "scheduled_posts":
            self._handle_scheduled_posts(call, user_id)
        elif data.startswith("remove_ch_"):
            channel_id = data[10:]
            self._handle_confirm_remove_channel(call, user_id, channel_id)
        elif data.startswith("scheduled_detail_"):
            post_id = data[17:]
            self._handle_scheduled_detail(call, user_id, post_id)
        elif data.startswith("delete_scheduled_"):
            post_id = data[17:]
            self._handle_delete_scheduled(call, user_id, post_id)
        elif data == "back_to_main":
            self._handle_back_to_main(call)
        elif data == "cancel":
            self._handle_cancel(call, user_id)
    
    def _handle_post_now(self, call, user_id: int):
        """Обработка немедленной отправки"""
        channels = self.database.get_user_channels(user_id)
        
        if not channels:
            self.bot.edit_message_text(
                MESSAGES["no_channels"],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        self.set_user_state(user_id, "waiting_post_message")
        self.bot.edit_message_text(
            MESSAGES["enter_message"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.cancel_keyboard()
        )
    
    def _handle_schedule_post(self, call, user_id: int):
        """Обработка планирования поста"""
        channels = self.database.get_user_channels(user_id)
        
        if not channels:
            self.bot.edit_message_text(
                MESSAGES["no_channels"],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        self.set_user_state(user_id, "waiting_schedule_message")
        self.bot.edit_message_text(
            MESSAGES["enter_schedule_message"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.cancel_keyboard()
        )

    def _handle_add_channel(self, call, user_id: int):
        """Добавление канала"""
        self.set_user_state(user_id, "waiting_channel_id")
        self.bot.edit_message_text(
            MESSAGES["enter_channel_id"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.cancel_keyboard()
        )
    
    def _handle_remove_channel(self, call, user_id: int):
        """Удаление канала"""
        channels = self.database.get_user_channels(user_id)
        
        if not channels:
            self.bot.edit_message_text(
                MESSAGES["no_channels"],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        self.bot.edit_message_text(
            "🗑 Выберите канал/группу для удаления:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.channel_list(channels, "remove")
        )
    
    def _handle_list_channels(self, call, user_id: int):
        """Список каналов"""
        channels = self.database.get_user_channels(user_id)
        
        if not channels:
            message = MESSAGES["no_channels"]
        else:
            message = "📋 Ваши каналы и группы:\n\n"
            for channel_id, channel_info in channels.items():
                message += f"📢 {channel_info['title']}\n"
                message += f"   ID: {channel_id}\n\n"
        
        self.bot.edit_message_text(
            message,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.main_menu()
        )
    
    def _handle_scheduled_posts(self, call, user_id: int):
        """Запланированные посты"""
        posts = self.database.get_user_scheduled_posts(user_id)
        
        if not posts:
            self.bot.edit_message_text(
                MESSAGES["no_scheduled"],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        self.bot.edit_message_text(
            MESSAGES["scheduled_list"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.scheduled_posts_list(posts)
        )
    
    def _handle_confirm_remove_channel(self, call, user_id: int, channel_id: str):
        """Подтверждение удаления канала"""
        import asyncio
        success = asyncio.run(self.database.remove_user_channel(user_id, channel_id))
        
        if success:
            self.bot.edit_message_text(
                MESSAGES["channel_removed"],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
        else:
            self.bot.edit_message_text(
                "❌ Ошибка при удалении канала",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
    
    def _handle_scheduled_detail(self, call, user_id: int, post_id: str):
        """Детали запланированного поста"""
        posts = self.database.get_user_scheduled_posts(user_id)
        post = next((p for p in posts if p["id"] == post_id), None)
        
        if not post:
            self.bot.edit_message_text(
                "❌ Пост не найден",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        schedule_time = datetime.fromisoformat(post["schedule_time"])
        message = f"⏰ Запланированный пост:\n\n"
        message += f"📅 Время: {schedule_time.strftime('%d.%m.%Y %H:%M')}\n"
        message += f"📝 Сообщение: {post['message'][:100]}{'...' if len(post['message']) > 100 else ''}\n"
        message += f"📢 Каналов: {len(post['channels'])}"
        
        self.bot.edit_message_text(
            message,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.scheduled_post_detail(post_id)
        )
    
    def _handle_delete_scheduled(self, call, user_id: int, post_id: str):
        """Удаление запланированного поста"""
        import asyncio
        success = asyncio.run(self.database.remove_scheduled_post(post_id))
        
        if success:
            self.bot.edit_message_text(
                MESSAGES["scheduled_deleted"],
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
        else:
            self.bot.edit_message_text(
                "❌ Ошибка при удалении поста",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.keyboards.main_menu()
            )
    
    def _handle_back_to_main(self, call):
        """Возврат в главное меню"""
        self.bot.edit_message_text(
            "🛠 Главное меню управления ботом:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.main_menu()
        )
    
    def _handle_cancel(self, call, user_id: int):
        """Отмена операции"""
        self.clear_user_state(user_id)
        self.bot.edit_message_text(
            "❌ Операция отменена. Выберите действие:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=self.keyboards.main_menu()
        )
