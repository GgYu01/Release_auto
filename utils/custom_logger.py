from loguru import logger
from config.logging_config import LoggingConfig
import logging
import contextvars
import json

class Logger:
    def __init__(self, name, logging_config=None):
        self.name = name
        if logging_config is None:
            logging_config = LoggingConfig()
        self.logging_config = logging_config
        logger.remove()
        logger.add(logging_config.log_file, format=logging_config.log_format, level=logging_config.log_level, rotation=logging_config.log_rotation, retention=logging_config.log_retention, compression=logging_config.log_compression, catch=True)

    def debug(self, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=False).debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=False).info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=False).warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=False).error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=False).critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=True).exception(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        logger.bind(name=self.name).opt(depth=1, exception=False).log(level, msg, *args, **kwargs)

# Context variable for request tracking
request_id_var = contextvars.ContextVar('request_id')

def set_request_id(request_id: str):
    request_id_var.set(request_id)

def get_request_id():
    return request_id_var.get(None)  # Return None if not set
