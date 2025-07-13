import os
from dotenv import load_dotenv


def get_env(key, default=None):
    load_dotenv(override=True)
    return os.getenv(key, default)
