import sqlite3
import json
import pickle
from telegram.ext import BasePersistence
from collections import defaultdict
from typing import Dict, Any, Tuple, Optional, cast

class SQLitePersistence(BasePersistence):
    """
    A class for SQLite-based persistence for python-telegram-bot.
    """

    def __init__(self, filepath: str, store_user_data: bool = True, store_chat_data: bool = True, store_bot_data: bool = True):
        super().__init__(store_user_data=store_user_data, store_chat_data=store_chat_data, store_bot_data=store_bot_data)
        self.filepath = filepath
        self.conn = sqlite3.connect(self.filepath, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                user_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_data (
                chat_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_data (
                key TEXT PRIMARY KEY DEFAULT 'bot_data',
                data TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                name TEXT NOT NULL,
                conv_key TEXT NOT NULL,
                state BLOB,
                PRIMARY KEY (name, conv_key)
            )
        ''')
        # A table for callback_data, storing it as a pickled blob
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS callback_data (
                key TEXT PRIMARY KEY DEFAULT 'callback_data',
                data BLOB NOT NULL
            )
        ''')
        self.conn.commit()

    async def get_user_data(self) -> Dict[int, Dict[Any, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, data FROM user_data")
        rows = cursor.fetchall()
        user_data = defaultdict(dict)
        for user_id, data in rows:
            user_data[user_id] = json.loads(data)
        return user_data

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        cursor = self.conn.cursor()
        json_data = json.dumps(data)
        cursor.execute("INSERT OR REPLACE INTO user_data (user_id, data) VALUES (?, ?)", (user_id, json_data))
        self.conn.commit()

    async def drop_user_data(self, user_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM user_data WHERE user_id = ?", (user_id,))
        self.conn.commit()

    async def get_chat_data(self) -> Dict[int, Dict[Any, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT chat_id, data FROM chat_data")
        rows = cursor.fetchall()
        chat_data = defaultdict(dict)
        for chat_id, data in rows:
            chat_data[chat_id] = json.loads(data)
        return chat_data

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        cursor = self.conn.cursor()
        json_data = json.dumps(data)
        cursor.execute("INSERT OR REPLACE INTO chat_data (chat_id, data) VALUES (?, ?)", (chat_id, json_data))
        self.conn.commit()

    async def drop_chat_data(self, chat_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM chat_data WHERE chat_id = ?", (chat_id,))
        self.conn.commit()

    async def get_bot_data(self) -> Dict[Any, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT data FROM bot_data WHERE key = 'bot_data'")
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}

    async def update_bot_data(self, data: Dict) -> None:
        cursor = self.conn.cursor()
        json_data = json.dumps(data)
        cursor.execute("INSERT OR REPLACE INTO bot_data (key, data) VALUES ('bot_data', ?)", (json_data,))
        self.conn.commit()

    async def get_conversations(self, name: str) -> Dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT conv_key, state FROM conversations WHERE name = ?", (name,))
        rows = cursor.fetchall()
        conversations = {}
        for conv_key_str, state_blob in rows:
            conv_key = tuple(json.loads(conv_key_str))
            if state_blob:
                state = pickle.loads(state_blob)
            else:
                state = None
            conversations[conv_key] = state
        return conversations

    async def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        cursor = self.conn.cursor()
        conv_key_str = json.dumps(key)
        if new_state is None:
            cursor.execute("DELETE FROM conversations WHERE name = ? AND conv_key = ?", (name, conv_key_str))
        else:
            state_blob = pickle.dumps(new_state)
            cursor.execute("INSERT OR REPLACE INTO conversations (name, conv_key, state) VALUES (?, ?, ?)", (name, conv_key_str, state_blob))
        self.conn.commit()

    async def get_callback_data(self) -> Optional[Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT data FROM callback_data WHERE key = 'callback_data'")
        row = cursor.fetchone()
        if row:
            return pickle.loads(row[0])
        return None

    async def update_callback_data(self, data: Any) -> None:
        cursor = self.conn.cursor()
        pickled_data = pickle.dumps(data)
        cursor.execute("INSERT OR REPLACE INTO callback_data (key, data) VALUES ('callback_data', ?)", (pickled_data,))
        self.conn.commit()

    async def refresh_bot_data(self, bot_data: Dict) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> None:
        pass

    async def refresh_user_data(self, user_id: int, user_data: Dict) -> None:
        pass

    async def flush(self) -> None:
        if self.conn:
            self.conn.commit()

    async def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()
