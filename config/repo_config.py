from abc import ABC, abstractmethod
from typing import Dict, List
from pathlib import Path
from functools import lru_cache
import threading

@dataclass
class SingletonMeta(type):
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]

class BaseRepositoryConfig(ABC, metaclass=SingletonMeta):

    @abstractmethod
    def load_config(self):
        pass

    @property
    @abstractmethod
    def repo_name(self) -> str:
        pass

    @property
    @abstractmethod
    def repo_path(self) -> Path:
        pass

    @property
    @abstractmethod
    def parent_repo(self) -> str:
        pass

    @property
    @abstractmethod
    def module_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_independent(self) -> bool:
        pass

    @property
    @abstractmethod
    def manifest_path(self) -> Path:
        pass

    @property
    @abstractmethod
    def tag_prefix(self) -> str:
        pass

    @property
    @abstractmethod
    def generate_patch(self) -> bool:
        pass

    @property
    @abstractmethod
    def current_commit(self) -> str:
        pass

    @property
    @abstractmethod
    def latest_tag(self) -> str:
        pass

    @property
    @abstractmethod
    def second_latest_tag(self) -> str:
        pass

    @property
    @abstractmethod
    def branch(self) -> str:
        pass

    @property
    @abstractmethod
    def patch_strict_mode(self) -> bool:
        pass

    @property
    @abstractmethod
    def no_commit_analysis(self) -> bool:
        pass

    # Other abstract properties and methods as needed

@dataclass(frozen=True)
class NebulaRepoConfig(BaseRepositoryConfig):
    repo_name: str = "nebula"
    repo_path: Path = Path("/home/nebula/grpower/workspace/nebula")
    parent_repo: str = "nebula"
    is_independent: bool = False
    manifest_path: Path = Path("/home/nebula/grpower/workspace/nebula/manifest/cci/nebula-main")
    tag_prefix: str = "release-spm.mt8678_mt8676_"
    generate_patch: bool = False
    analyze_commit: bool = True
    branch: str = "nebula"
    special_branch_rules: Dict[str, str] = field(default_factory=lambda: {
        "zircon": "release-spm.mt8678_mtk",
        "garnet": "release-spm.mt8678_mtk"
    })
    patch_strict_mode: bool = False
    no_commit_analysis: bool = False

    def load_config(self):
        pass

@dataclass(frozen=True)
class YoctoRepoConfig(BaseRepositoryConfig):
    repo_name: str = "yocto"
    repo_path: Path = Path("/home/nebula/yocto")
    parent_repo: str = "yocto"
    is_independent: bool = False
    manifest_path: Path = Path("/home/nebula/yocto/.repo/manifests/mt8678/grt/1114/yocto.xml")
    tag_prefix: str = "release-spm.mt8678_"
    generate_patch: bool = True
    analyze_commit: bool = True
    branch: str = "release-spm.mt8678_2024_1114"
    special_branch_rules: Dict[str, str] = field(default_factory=dict)
    patch_strict_mode: bool = False
    no_commit_analysis: bool = False

    def load_config(self):
        pass

@dataclass(frozen=True)
class GrtRepoConfig(BaseRepositoryConfig):
    repo_name: str = "grt"
    repo_path: Path = Path("/home/nebula/grt")
    parent_repo: str = "grt"
    is_independent: bool = True
    manifest_path: Path = None
    tag_prefix: str = "release-spm.mt8678_"
    generate_patch: bool = True
    analyze_commit: bool = True
    branch: str = "release-spm.mt8678_2024_1114"
    special_branch_rules: Dict[str, str] = field(default_factory=dict)
    patch_strict_mode: bool = False
    no_commit_analysis: bool = False

    def load_config(self):
        pass


REPO_CONFIGS: List[BaseRepositoryConfig] = [
    NebulaRepoConfig(),
    YoctoRepoConfig(),
    GrtRepoConfig()
]
