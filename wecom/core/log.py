import os.path
import logging
from logging.handlers import RotatingFileHandler


def get_logger(app=None):
    _logger = logging.getLogger("chatgpt-wecom")
    _logger.setLevel(logging.DEBUG)

    dir_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_path = os.path.join(dir_path, "logs")

    if not os.path.exists(log_path):
        os.makedirs(log_path, exist_ok=True)

    filename = os.path.join(log_path, "app.log")
    print(log_path, filename)
    formatter = logging.Formatter("%(asctime)s [%(filename)s line:%(lineno)d] - %(name)s - %(levelname)s - %(message)s")

    # 创建一个StreamHandler用于输出到控制台
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    # 创建一个文件处理器，# 创建一个文件处理器，并设置级别为DEBUG
    # 创建一个RotatingFileHandler，当文件达到200MB时分割，最多保留5个备份文件
    file_handler = RotatingFileHandler(filename, maxBytes=100 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 添加处理器到日志记录器
    if app is not None:
        app.logger.addHandler(file_handler)
        app.logger.addHandler(stream_handler)
    else:
        _logger.addHandler(stream_handler)
        _logger.addHandler(file_handler)

    return _logger


logger = get_logger()
