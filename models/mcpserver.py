from typing import Optional, List
from utils.db_operations import Database

class MCPServerRepository:
    """MCP服务器数据访问层(异步版)"""
    
    def __init__(self):
        self.db = Database()
    
    async def _init_table(self):
        """初始化MCP服务器表结构"""
        columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'mcpname': 'TEXT NOT NULL',
            'url': 'TEXT NOT NULL'
        }
        await self.db.create_table('mcpservers', columns)
    
    async def add_server(self, mcpname: str, url: str) -> int:
        """添加MCP服务器"""
        cursor = await self.db.execute(
            "INSERT INTO mcpservers (mcpname, url) VALUES (?, ?)",
            (mcpname, url)
        )
        await self.db.commit()
        return cursor.lastrowid
    
    async def get_server(self, server_id: int) -> Optional[dict]:
        """获取单个服务器信息"""
        cursor = await self.db.execute(
            "SELECT * FROM mcpservers WHERE id = ?",
            (server_id,)
        )
        if row := await cursor.fetchone():
            return dict(row)
        return None
    
    async def get_all_servers(self) -> List[dict]:
        """获取所有服务器列表"""
        cursor = await self.db.execute("SELECT * FROM mcpservers")
        results = await cursor.fetchall()
        print(f"Debug - 查询到记录数: {len(results)}")
        return [dict(row) for row in results]