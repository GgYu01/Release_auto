from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme
import logging

class RichLogger:
    def __init__(self, name, log_file="release.log"):
        custom_theme = Theme({"info":"cyan","warning": "magenta", "error": "bold red"})
        self.console = Console(theme=custom_theme, record=True)
        self.log_file = log_file

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = RichHandler(
                rich_tracebacks=True,
                tracebacks_suppress=[
                    
                ]
            )
            self.logger.addHandler(handler)

    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
        self._write_log_to_file("INFO", message)

    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)
        self._write_log_to_file("WARNING", message)

    def error(self, message, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)
        self._write_log_to_file("ERROR", message)

    def _write_log_to_file(self, level, message):
        with open(self.log_file, "a") as f:
            f.write(f"{level}: {message}\n")

    def save_html(self, path='log.html'):
      self.console.save_html(path)
