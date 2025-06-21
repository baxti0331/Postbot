"""
Управление базой данных бота
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

class Database:
    def __init__(self, filename: str = "bot_data.json"):
        self.filename = filename
        self.data = self._load_data()
        self._lock = asyncio.Lock()
    
    def _load_data(self) -> dict:
        """Загрузка данных из файла"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Структура по умолчанию
        return {
            "users": {},
            "scheduled_posts": []
        }
    
    async def _save_data(self):
        """Сохранение данных в файл"""
        async with self._lock:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    async def add_user_channel(self, user_id: int, channel_id: str, channel_title: str) -> bool:
        """Добавление канала/группы для пользователя"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.data["users"]:
            self.data["users"][user_id_str] = {"channels": {}}
        
        user_channels = self.data["users"][user_id_str]["channels"]
        
        # Проверка лимита каналов
        from config import MAX_CHANNELS_PER_USER
        if len(user_channels) >= MAX_CHANNELS_PER_USER:
            return False
        
        # Добавление канала
        user_channels[channel_id] = {
            "title": channel_title,
            "added_at": datetime.now().isoformat()
        }
        
        await self._save_data()
        return True
    
    async def remove_user_channel(self, user_id: int, channel_id: str) -> bool:
        """Удаление канала/группы пользователя"""
        user_id_str = str(user_id)
        
        if (user_id_str in self.data["users"] and 
            channel_id in self.data["users"][user_id_str]["channels"]):
            
            del self.data["users"][user_id_str]["channels"][channel_id]
            await self._save_data()
            return True
        
        return False
    
    def get_user_channels(self, user_id: int) -> Dict[str, dict]:
        """Получение каналов/групп пользователя"""
        user_id_str = str(user_id)
        
        if user_id_str in self.data["users"]:
            return self.data["users"][user_id_str]["channels"]
        
        return {}
    
    async def add_scheduled_post(self, user_id: int, message: str, 
                               schedule_time: datetime, channels: List[str]) -> str:
        """Добавление запланированного поста"""
        post_id = f"{user_id}_{int(schedule_time.timestamp())}"
        
        scheduled_post = {
            "id": post_id,
            "user_id": user_id,
            "message": message,
            "schedule_time": schedule_time.isoformat(),
            "channels": channels,
            "created_at": datetime.now().isoformat()
        }
        
        self.data["scheduled_posts"].append(scheduled_post)
        await self._save_data()
        return post_id
    
    def get_due_posts(self) -> List[dict]:
        """Получение постов, готовых к отправке"""
        now = datetime.now()
        due_posts = []
        
        for post in self.data["scheduled_posts"]:
            schedule_time = datetime.fromisoformat(post["schedule_time"])
            if schedule_time <= now:
                due_posts.append(post)
        
        return due_posts
    
    async def remove_scheduled_post(self, post_id: str) -> bool:
        """Удаление запланированного поста"""
        for i, post in enumerate(self.data["scheduled_posts"]):
            if post["id"] == post_id:
                del self.data["scheduled_posts"][i]
                await self._save_data()
                return True
        
        return False
    
    def get_user_scheduled_posts(self, user_id: int) -> List[dict]:
        """Получение запланированных постов пользователя"""
        return [post for post in self.data["scheduled_posts"] 
                if post["user_id"] == user_id]
