import logging
from config.logging_config import LOGGING_CONFIG
import functools
import time
import os

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(LOGGING_CONFIG.log_level)
        formatter = logging.Formatter(LOGGING_CONFIG.log_format)
        if not os.path.exists(os.path.dirname(LOGGING_CONFIG.log_file_path)):
            os.makedirs(os.path.dirname(LOGGING_CONFIG.log_file_path))
        file_handler = logging.FileHandler(LOGGING_CONFIG.log_file_path)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

def log_and_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = Logger().logger
        logger.debug(f"Entering {func.__name__}")
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.debug(f"Exiting {func.__name__}, Time taken: {elapsed_time:.4f}s")
        return result
    return wrapper
