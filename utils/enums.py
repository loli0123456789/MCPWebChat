from enum import Enum

class ErrCode(Enum):
    """错误码枚举类"""
    
    SUCCESS = (0, "操作成功")
    FAILURE = (-1, "发生错误")
    EXCEPTION = (-99, "服务异常")

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    @property
    def value(self):
        """获取错误码值"""
        return self.code

    def __str__(self):
        """格式化输出"""
        return f"[{self.code}] {self.msg}"

class ChatRole(Enum):
    """
    对话角色
    """
    USER = "user"
    AGENT = "agent"
    
class LLMRole(Enum):
    """
    LLM对话角色
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    

    
