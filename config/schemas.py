from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal

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
    commit_details: List[Dict[str, str]] = field(default_factory=list)
    newest_version: Optional[str] = None
    next_newest_version: Optional[str] = None
    analyze_commit: bool = False
    generate_patch: bool = False
    branch_info: Optional[str] = None
    special_branch_repos: Dict[str, Dict[str, str]] = field(default_factory=dict)
    push_template: Optional[str] = None
    logging_config: LoggingConfig = field(default_factory=LoggingConfig)
    merge_config: Optional['MergeConfig'] = None


@dataclass
class MergeConfig:
    merge_mode: Literal['auto', 'manual', 'disabled'] = 'disabled'

@dataclass
class RepoConfig:
    repo_name: str
    repo_type: str
    path: str
    sync_strategy: Optional[str] = None
    merge_config: Optional[MergeConfig] = None
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
class FileCopyOperation:
    source_path: str
    destination_path: str
    is_wildcard: bool = False

@dataclass
class BuildTypeConfig:
    name: str
    enabled: bool = False
    pre_build_clean: bool = True
    post_build_git: bool = True
    post_build_copy_operations: List[FileCopyOperation] = field(default_factory=list)

@dataclass
class BuildConfig:
    build_types: Dict[str, BuildTypeConfig] = field(default_factory=lambda: {
        "nebula-sdk": BuildTypeConfig(name="nebula-sdk"),
        "nebula": BuildTypeConfig(
            name="nebula",
            enabled=True,
            pre_build_clean=False,
            post_build_copy_operations=[
                FileCopyOperation(source_path="products/mt8678-mix/out/gz.img", destination_path="gz.img"),
                FileCopyOperation(source_path="vmm/out/nbl_vmm", destination_path="nbl_vmm"),
                FileCopyOperation(source_path="vmm/out/nbl_vm_ctl", destination_path="nbl_vm_ctl"),
                FileCopyOperation(source_path="vmm/out/nbl_vm_srv", destination_path="nbl_vm_srv"),
                FileCopyOperation(source_path="vmm/out/libvmm.so", destination_path="libvmm.so"),
                FileCopyOperation(source_path="third_party/prebuilts/libluajit/lib64/libluajit.so", destination_path="libluajit.so"),
                FileCopyOperation(source_path="products/mt8678-mix/guest-configs/uos_alps_pv8678.lua", destination_path="uos_alps_pv8678.lua"),
                FileCopyOperation(source_path="vmm/nbl_vm_srv/data/vm_srv_cfg_8678.pb.txt", destination_path="vm_srv_cfg_8678.pb.txt"),
                FileCopyOperation(source_path="vmm/nbl_vmm/data/uos_mtk8678/uos_bootloader_lk2.pb.txt", destination_path="uos_bootloader_lk2.pb.txt"),
                FileCopyOperation(source_path="vmm/out/symbols/*", destination_path="symbols/", is_wildcard=True),
                FileCopyOperation(source_path="vmm/nbl_vmm/data/vm_audio_cfg.pb.txt", destination_path="vm_audio_cfg.pb.txt"),
                FileCopyOperation(source_path="vmm/nbl_vm_srv/data/nbl_ta_monitor", destination_path="nbl_ta_monitor"),
            ]
        ),
        "TEE": BuildTypeConfig(name="TEE")
    })
    paths: BuildPathConfig = field(default_factory=BuildPathConfig)
    git: BuildGitConfig = field(default_factory=BuildGitConfig)
    enable_environment_cleanup: bool = True
    max_concurrent_builds: int = 1
    build_timeout_seconds: int = 3600
    max_git_retries: int = 3
