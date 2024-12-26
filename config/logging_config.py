from dataclasses import dataclass
import yaml
from pathlib import Path

@dataclass
class LoggingConfig:
    log_file_path: str = 'logs/release.log'
    log_level: str = 'DEBUG'
    log_format: str = '[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s'

    @classmethod
    def load(cls, config_path=None):
        inst = cls()
        if config_path and Path(config_path).exists():
            with open(config_path,'r') as f:
                c=yaml.safe_load(f)
                for k,v in c.get('logging',{}).items():
                    setattr(inst,k,v)
        return inst

LOGGING_CONFIG = LoggingConfig.load()