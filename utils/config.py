import json
import os

config_file_path = "config/config.json"


def get_config():
    # 获取当前文件（这个.py文件）所在的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "../config/config.json")
    json_obj = json.load(open(config_file_path, "r"))
    return json_obj


Config = get_config()
