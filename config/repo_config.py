from typing import Dict, List, Optional
from pathlib import Path
import threading
from dataclasses import dataclass, field

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

@dataclass
class BaseRepositoryConfig:
    repo_name: str
    repo_path: Path
    parent_repo: Optional[str] = None
    module_name: Optional[str] = None
    is_independent: bool = False
    manifest_path: Optional[Path] = None
    manifest_type: Optional[str] = ""
    tag_prefix: str = ""
    generate_patch: bool = False
    current_commit: Optional[str] = None
    latest_tag: str = ""
    second_latest_tag: str = ""
    analyze_commit: bool = True
    branch: str = ""
    patch_strict_mode: bool = False
    no_commit_analysis: bool = False
    git_remotes: Dict[str, str] = field(default_factory=dict)
    git_push_template: str = ""

    def __post_init__(self):
        if not self.git_push_template:
            self.git_push_template = self.generate_git_push_template()

    def generate_git_push_template(self):
        return ""

    def load_config(self):
        pass

@dataclass
class NebulaRepoConfig(BaseRepositoryConfig):
    repo_name: str = "nebula"
    repo_path: Path = Path("/home/nebula/grpower/workspace/nebula")
    parent_repo: str = "nebula"
    is_independent: bool = False
    manifest_path: Path = Path("/home/nebula/grpower/workspace/nebula/manifest/cci/nebula-main")
    manifest_type: str = "jiri"
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

    def git_push_template(self) -> str:
        return f"HEAD:refs/for/{self.branch}"

@dataclass
class YoctoRepoConfig(BaseRepositoryConfig):
    repo_name: str = "yocto"
    repo_path: Path = Path("/home/nebula/yocto")
    parent_repo: str = "yocto"
    is_independent: bool = False
    manifest_path: Path = Path("/home/nebula/yocto/.repo/manifests/mt8678/grt/1114/yocto.xml")
    manifest_type: str = "repo"
    tag_prefix: str = "release-spm.mt8678_"
    generate_patch: bool = True
    analyze_commit: bool = True
    branch: str = "release-spm.mt8678_2024_1114"
    special_branch_rules: Dict[str, str] = field(default_factory=dict)
    patch_strict_mode: bool = False
    no_commit_analysis: bool = False

    def load_config(self):
        pass

@dataclass
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
