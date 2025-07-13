from typing import Optional, List
from utils.db_operations import Database

class MessageRepository:
    """消息数据访问层(异步版)"""
    
    def __init__(self):
        self.db = Database()
    
    async def _init_table(self):
        """初始化消息表结构"""
        columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'conversation_id': 'INTEGER NOT NULL',
            'role': 'TEXT NOT NULL',  # 可以是'system', 'user', 'assistant'
            'content': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'FOREIGN KEY(conversation_id)': 'REFERENCES conversations(id)'
        }
        await self.db.create_table('messages', columns)
    
    async def add_message(self, conversation_id: int, role: str, content: str) -> int:
        """添加新消息"""
        cursor = await self.db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        await self.db.commit()
        return cursor.lastrowid
    
    async def get_messages(self, conversation_id: int) -> List[dict]:
        """获取对话的所有消息"""
        cursor = await self.db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        results = await cursor.fetchall()
        return [dict(row) for row in results]
    
    async def get_message(self, message_id: int) -> Optional[dict]:
        """获取单个消息信息"""
        cursor = await self.db.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,)
        )
        if row := await cursor.fetchone():
            return dict(row)
        return None

    async def update_message(self, message_id: int, content: str) -> bool:
        """更新消息内容"""
        try:
            cursor = await self.db.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (content, message_id)
            )
            await self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"更新消息时出错: {e}")
            return False