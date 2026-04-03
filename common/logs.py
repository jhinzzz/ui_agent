import os
import time
import uuid
from datetime import datetime
import sys
from loguru import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def _generate_logs_dir():
    cur_time = time.strftime("%Y-%m-%d")
    dirname = os.path.join(LOGS_DIR, cur_time)
    try:
        if not os.path.exists(dirname):
            os.makedirs(dirname)
    except OSError as e:
        print(f"创建目录 {dirname} 时出错: {e}")
    return dirname


def _init_logger():
    log_dir = _generate_logs_dir()
    log_time = datetime.now().strftime("%H:%M:%S")
    log_id = str(uuid.uuid4())[:8]
    log_file = f"{log_dir}/test_{log_time}_{log_id}.log"

    logger.remove()

    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level="INFO",
        colorize=True,
    )

    logger.add(
        log_file,
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        enqueue=True,
        catch=True,
        serialize=False
    )


_init_logger()


class Logger:
    def __init__(self, name: str = None):
        self.name = name

    def info(self, msg):
        if self.name:
            logger.bind(name=self.name).info(msg)
        else:
            logger.info(msg)

    def debug(self, msg):
        if self.name:
            logger.bind(name=self.name).debug(msg)
        else:
            logger.debug(msg)

    def warning(self, msg):
        if self.name:
            logger.bind(name=self.name).warning(msg)
        else:
            logger.warning(msg)

    def error(self, msg):
        if self.name:
            logger.bind(name=self.name).error(msg)
        else:
            logger.error(msg)


log = Logger()
