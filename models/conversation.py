from typing import Optional, List
from utils.db_operations import Database

class ConversationRepository:
    """对话数据访问层(异步版)"""
    
    def __init__(self):
        self.db = Database()
    
    async def _init_table(self):
        """初始化对话表结构"""
        columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'agentid': 'TEXT NOT NULL',
            'name': 'TEXT NOT NULL',
            'createtime': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'userid': 'TEXT NOT NULL'
        }
        await self.db.create_table('conversations', columns)
    
    async def add_conversation(self, agentid: str, name: str, userid: str) -> int:
        """添加新对话"""
        cursor = await self.db.execute(
            "INSERT INTO conversations (agentid, name, userid) VALUES (?, ?, ?)",
            (agentid, name, userid)
        )
        await self.db.commit()
        return cursor.lastrowid
    
    async def get_conversation(self, conversation_id: int) -> Optional[dict]:
        """获取单个对话信息"""
        cursor = await self.db.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        if row := await cursor.fetchone():
            return dict(row)
        return None
    
    async def get_user_conversations(self, userid: str) -> List[dict]:
        """获取用户的所有对话"""
        cursor = await self.db.execute(
            "SELECT * FROM conversations WHERE userid = ? ORDER BY createtime DESC",
            (userid,)
        )
        results = await cursor.fetchall()
        return [dict(row) for row in results]