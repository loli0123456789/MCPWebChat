import aiosqlite
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent / 'data' / 'app.db'

class Database:
    """基础数据库操作类(异步版)，只负责通用CRUD"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = None
        return cls._instance
    
    async def _get_connection(self):
        """获取异步数据库连接"""
        if not self.conn:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.conn = await aiosqlite.connect(str(DB_PATH))
            self.conn.row_factory = aiosqlite.Row
        return self.conn
    
    async def execute(self, sql: str, params: tuple = None) -> aiosqlite.Cursor:
        """执行SQL语句"""
        conn = await self._get_connection()
        return await conn.execute(sql, params or ())
    
    async def commit(self):
        """提交事务"""
        conn = await self._get_connection()
        await conn.commit()
    
    async def create_table(self, table_name: str, columns: Dict[str, str], constraints: List[str] = None):
        """
        通用建表方法(异步)
        :param table_name: 表名
        :param columns: 列定义字典 {列名: 数据类型}
        :param constraints: 表级约束条件列表
        """
        columns_sql = ', '.join(f"{name} {type}" for name, type in columns.items())
        constraints_sql = ', '.join(constraints) if constraints else ''
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql}{', ' + constraints_sql if constraints_sql else ''})"
        await self.execute(sql)
        await self.commit()