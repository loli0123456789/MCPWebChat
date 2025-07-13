from typing import Optional
from utils.db_operations import Database

class UserRepository:
    """用户数据访问层"""
    
    def __init__(self):
        self.db = Database()
        self._init_table()
    
    def _init_table(self):
        """初始化用户表结构"""
        columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'username': 'TEXT UNIQUE NOT NULL',
            'password': 'TEXT NOT NULL',
            'email': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        self.db.create_table('users', columns)
    
    def add_user(self, username: str, password: str, email: Optional[str] = None) -> int:
        """添加用户"""
        cursor = self.db.execute(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            (username, password, email)
        )
        self.db.commit()
        return cursor.lastrowid
    
    def get_user(self, username: str) -> Optional[dict]:
        """获取用户信息"""
        cursor = self.db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        if row := cursor.fetchone():
            return dict(row)
        return None