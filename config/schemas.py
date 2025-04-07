from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"

@dataclass
class GitRepoInfo:
    repo_name: str
    repo_parent: str
    path: str
    repo_path: str
    repo_type: str
    tag_prefix: Optional[str] = None
    remote_name: Optional[str] = None
    local_branch: Optional[str] = None
    remote_branch: Optional[str] = None
    parent_repo: Optional[str] = None
    commit_analyses: List[Dict] = field(default_factory=list)
    newest_version: Optional[str] = None
    next_newest_version: Optional[str] = None
    analyze_commit: bool = False
    generate_patch: bool = False
    branch_info: Optional[str] = None
    special_branch_repos: Dict[str, Dict[str, str]] = field(default_factory=dict)
    push_template: Optional[str] = None
    logging_config: LoggingConfig = field(default_factory=LoggingConfig)

@dataclass
class RepoConfig:
    repo_name: str
    repo_type: str
    path: str
    sync_strategy: Optional[str] = None
    remote_name: Optional[str] = None
    remote_branch: Optional[str] = None
    local_branch: Optional[str] = None
    git_repos: List[GitRepoInfo] = field(default_factory=list)
    manifest_path: Optional[str] = None
    default_tag_prefix: Optional[str] = None
    parent_repo: Optional[str] = None
    manifest_type: Optional[str] = None
    default_analyze_commit: bool = False
    default_generate_patch: bool = False
    all_branches: List[str] = field(default_factory=list)
    special_branch_repos: Dict[str, str] = field(default_factory=dict)
    logging_config: LoggingConfig = field(default_factory=LoggingConfig)

@dataclass
class SyncAction:
    action_type: str
    action_params: Dict

@dataclass
class SyncStrategyConfig:
    strategy_name: str
    parent_types: List[str]
    sync_actions: List[SyncAction]

@dataclass
class AllReposConfig:
    repo_configs: Dict[str, RepoConfig] = field(default_factory=dict)

    def all_git_repos(self):
        for repo_config in self.repo_configs.values():
            for git_repo in repo_config.git_repos:
                yield git_repo

@dataclass
class AllSyncConfigs:
    sync_configs: Dict[str, SyncStrategyConfig] = field(default_factory=dict)

@dataclass
class VersionIdentifierConfig:
    manual_identifier: Optional[str] = None

@dataclass
class BuildPathConfig:
    grpower_workspace: str = "~/grpower/workspace"
    nebula_out: str = "~/grpower/workspace/nebula/out"
    grt_path: str = "~/grt"
    thyp_sdk_path: str = "~/grt/thyp-sdk"
    yocto_path: str = "~/yocto"
    alps_path: str = "~/alps"
    nebula_sdk_output: str = "/home/nebula/grt/nebula-sdk"
    prebuilt_images: str = "~/grt/thyp-sdk/products/mt8678-mix/prebuilt-images"
    tee_temp: str = "~/grt/teetemp"
    tee_kernel: str = "~/alps/vendor/mediatek/proprietary/trustzone/grt/source/common/kernel"
    yocto_hypervisor: str = "~/yocto/prebuilt/hypervisor/grt"

@dataclass
class BuildGitConfig:
    commit_author: str = "gaoyx <gaoyx@goldenrivertek.com>"
    commit_message_sdk: str = "chore(sdk): update nebula-sdk artifacts"
    commit_message_nebula: str = "chore(nebula): sync prebuilt images"
    commit_message_tee: str = "chore(tee): update TEE kernel binaries"
    remote_name: str = "origin"
    remote_branch_nebula: str = "release-spm.mt8678_2024_1230"
    remote_branch_tee: str = "release-spm.mt8678_2024_1230"
    push_template: str = "{remote_name} HEAD:refs/for/{remote_branch}"
    sdk_paths_to_add: List[str] = field(default_factory=lambda: ["ree", "run", "hee"])

@dataclass
class BuildTypeConfig:
    name: str
    enabled: bool = False
    pre_build_clean: bool = True
    post_build_git: bool = True

@dataclass
class BuildConfig:
    build_types: Dict[str, BuildTypeConfig] = field(default_factory=lambda: {
        "nebula-sdk": BuildTypeConfig(name="nebula-sdk"),
        "nebula": BuildTypeConfig(name="nebula" ,enabled=True ,pre_build_clean=False),
        "TEE": BuildTypeConfig(name="TEE")
    })
    paths: BuildPathConfig = field(default_factory=BuildPathConfig)
    git: BuildGitConfig = field(default_factory=BuildGitConfig)
    enable_environment_cleanup: bool = True
    max_concurrent_builds: int = 1
    build_timeout_seconds: int = 3600
    max_git_retries: int = 3
