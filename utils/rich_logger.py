import logging
import inspect
from config.logging_config import config as logging_config

class Logger:
    def __init__(self, name):
        """
        Initializes the Logger with the specified name.

        Args:
            name (str): The name of the logger.
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.setup_logger()

    def setup_logger(self):
        """Configures the logger."""
        formatter = logging.Formatter(logging_config["log_format"], style="{")
        handler = logging.FileHandler(logging_config["log_file"])
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)  # Explicitly set log level to INFO
        self.formatter = formatter        
        # Add extra fields to the logger for use in the log format
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record = old_factory(*args, **kwargs)
            record.time = self.formatTime(record)  # Add time field
            record.level = record.levelname  # Add level field
            frame = inspect.currentframe().f_back.f_back
            record.extra = {
                "name": self.name,
                "function": frame.f_code.co_name,
                "filename": frame.f_code.co_filename,
                "line": frame.f_lineno
            }
            return record

        logging.setLogRecordFactory(record_factory)

    def formatTime(self, record, datefmt=None):
        """
        Formats the time for the log record.

        Args:
            record (logging.LogRecord): The log record.
            datefmt (str, optional): The date format string. Defaults to None.

        Returns:
            str: The formatted time.
        """
        # Use the default formatter to format the time
        return self.formatter.formatTime(record, datefmt)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        self.logger.log(level, msg, *args, **kwargs)

    def save_html(self):
        """
        Saves the log as an HTML file. (Placeholder for future implementation)
        """
        pass
