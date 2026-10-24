from pathlib import Path

from decouple import config


BASE_DIR = Path(__file__).resolve().parent

CONDITIONS_FILE = "conditions.yml"
CONDITIONS_PATH = BASE_DIR / CONDITIONS_FILE

BOT_TOKEN = config("BOT_TOKEN")
DEBUG = config("DEBUG", default=False, cast=bool)

import logging

LOG_FILE = config("LOG_FILE", default="quando.log")
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

