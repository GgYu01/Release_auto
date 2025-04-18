import logging
from config.schemas import RepoConfig, AllReposConfig, ExcelConfig # Import ExcelConfig

logger = logging.getLogger(__name__)

grpower_config = RepoConfig(
    repo_name="grpower",
    repo_type="git",
    path="/home/nebula/grpower",
    sync_strategy="grpower_sync",
    remote_name="origin",
    remote_branch="nebula",
    local_branch="nebula",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
)

grt_config = RepoConfig(
    repo_name="grt",
    repo_type="git",
    path="/home/nebula/grt",
    sync_strategy="grt_grt_be_sync",
    remote_name="origin",
    remote_branch="release-spm.mt8678_2024_1230",
    local_branch="release-spm.mt8678_2024_1230",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
)

grt_be_config = RepoConfig(
    repo_name="grt_be",
    repo_type="git",
    path="/home/nebula/grt_be",
    sync_strategy="grt_grt_be_sync",
    remote_name="origin",
    remote_branch="release-spm.mt8678_2024_1230",
    local_branch="release-spm.mt8678_2024_1230",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
)

nebula_config = RepoConfig(
    repo_name="nebula",
    repo_type="jiri",
    path="/home/nebula/grpower/workspace/nebula",
    sync_strategy="nebula_sync",
    manifest_path="/home/nebula/grpower/workspace/nebula/manifest/cci/nebula-main",
    manifest_type="jiri",
    remote_name="origin",
    remote_branch="nebula",
    local_branch="nebula",
    default_tag_prefix="release-spm.mt8678_mt8676_",
    default_analyze_commit=True,
    default_generate_patch=False,
    all_branches=["nebula"],
    special_branch_repos={"zircon":{"remote_branch":"release-spm.mt8678_mtk","local_branch":"release-spm.mt8678_mtk"},"garnet":{"remote_branch":"release-spm.mt8678_mtk","local_branch":"release-spm.mt8678_mtk"}}
)

yocto_config = RepoConfig(
    repo_name="yocto",
    repo_type="repo",
    path="/home/nebula/yocto",
    sync_strategy="alps_yocto_sync",
    manifest_path="/home/nebula/yocto/.repo/manifests/mt8678/grt/1230/yocto.xml",
    manifest_type="repo",
    remote_name="grt-mt8678",
    remote_branch="release-spm.mt8678_2024_1230",
    local_branch="release-spm.mt8678_2024_1230",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
    all_branches=["release-spm.mt8678_2024_1230"],
)

alps_config = RepoConfig(
    repo_name="alps",
    repo_type="repo",
    path="/home/nebula/alps",
    sync_strategy="alps_yocto_sync",
    manifest_path="/home/nebula/alps/.repo/manifests/mt8678/grt/1230/alps.xml",
    manifest_type="repo",
    remote_name="grt-mt8678",
    remote_branch="release-spm.mt8678_2024_1230",
    local_branch="release-spm.mt8678_2024_1230",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
    all_branches=["release-spm.mt8678_2024_1230"],
)
# Configuration for Excel report generation
excel_config = ExcelConfig(
    enabled=True, # Enable report generation by default
    output_filename="ReleaseNotes.xlsx", # Default filename
    tester_name="Default Tester", # Placeholder tester name
    mtk_owner_serial="000000", # Placeholder serial
    zircon_repo_name="zircon", # Default zircon repo name
    garnet_repo_name="garnet" # Default garnet repo name
)


all_repos_config = AllReposConfig(
    repo_configs={
        "grt": grt_config,
        "nebula": nebula_config,
        # "alps": alps_config, # Add ALPS config
        # "yocto": yocto_config, # Add Yocto config
        # Add other configs like grpower, grt_be if they should be part of the flow
        # "grpower": grpower_config,
        # "grt_be": grt_be_config,
    },
    version_source_repo_name="grt",
    excel_config=excel_config # Assign the excel config instance
)
