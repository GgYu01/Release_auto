from loguru import logger

class Logger:
    def __init__(self, name):
        self.name = name
        logger.remove()
        logger.add("release.log", format="{time:YYYY-MM-DD HH:mm:ss} {level} {name} {function} {file}:{line} {message}")

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
