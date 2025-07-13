import argparse
from fastapi import FastAPI, Request
from pydantic import BaseModel


app = FastAPI()

# POST 接口示例
@app.post("/get_bmi")
async def get_bmi(request: Request):
    data = await request.json()
    height = float(data["height_m"])
    weight = int(data["weight_kg"])
    bmi = weight / (height * height)

    return {"bmi": bmi, "memo": "正常范围在22-24之间"}


@app.post("/get_recrangel_area")
async def get_recrangel_area(request: Request):
    data = await request.json()
    height = float(data["height"])
    weight = int(data["height"])
    area = height * height

    return {"area": area}


# 启动服务用的命令：uvicorn main:app --reload


# 命令行参数解析
parser = argparse.ArgumentParser(description="Start param")
parser.add_argument(
    "-p", "--port", type=int, nargs="?", default=10002, help="Set start port"
)

if __name__ == "__main__":
    args = parser.parse_args()
    port = args.port

    # 使用 Uvicorn 启动应用
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)
