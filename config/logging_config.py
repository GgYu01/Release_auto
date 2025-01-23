from dataclasses import dataclass, field

@dataclass
class LoggingConfig:
    log_file: str = "release.log"
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS!UTC} {level} {name} {function}:{line} {message}"
    log_level: str = "INFO"
    log_rotation: str = "500 MB"
    log_retention: str = "10 days"
    log_compression: str = "zip"

    def get_config(self):
        return self.__dict__
