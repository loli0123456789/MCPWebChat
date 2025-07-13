# 假设该类定义在 schemas.py 文件中，如果实际位置不同，请调整路径
from pydantic import BaseModel
from typing import Union


class ApiResponse(BaseModel):
    errCode: int
    errMsg: str
    data: Union[dict, list, int, str, None]  # 修改此处，允许 data 为字典或列表
    playload: str


