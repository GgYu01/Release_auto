from dataclasses import dataclass
from typing import Optional

@dataclass
class TaggingConfig:
    timezone: str = "Asia/Shanghai"
    grt_repo_name: str = "grt"
    manual_version_identifier: Optional[str] = None

    def get_config(self):
        return self.__dict__ 