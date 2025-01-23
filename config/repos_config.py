import logging
from config.schemas import RepoConfig, AllReposConfig

logger = logging.getLogger(__name__)

grpower_config = RepoConfig(
    repo_name="grpower",
    repo_type="git",
    path="~/grpower",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
)

grt_config = RepoConfig(
    repo_name="grt",
    repo_type="git",
    path="~/grt",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=False,
)

grt_be_config = RepoConfig(
    repo_name="grt_be",
    repo_type="git",
    path="~/grt_be",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=False,
    default_generate_patch=True,
)

nebula_config = RepoConfig(
    repo_name="nebula",
    repo_type="jiri",
    path="~/grpower/workspace/nebula",
    manifest_path="/home/nebula/grpower/workspace/nebula/manifest/cci/nebula-main",
    manifest_type="jiri",
    default_tag_prefix="release-spm.mt8678_mt8676_",
    default_analyze_commit=True,
    default_generate_patch=False,
    all_branches=["nebula"],
    special_branch_repos={"zircon":"release-spm.mt8678_mtk","garnet":"release-spm.mt8678_mtk"}
)

yocto_config = RepoConfig(
    repo_name="yocto",
    repo_type="repo",
    path="~/yocto",
    manifest_path="/home/nebula/yocto/.repo/manifests/mt8678/grt/1114/yocto.xml",
    manifest_type="repo",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
    all_branches=["release-spm.mt8678_2024_1114"],
)

alps_config = RepoConfig(
    repo_name="alps",
    repo_type="repo",
    path="~/alps",
    manifest_path="/home/nebula/alps/.repo/manifests/mt8678/grt/1114/alps.xml",
    manifest_type="repo",
    default_tag_prefix="release-spm.mt8678_",
    default_analyze_commit=True,
    default_generate_patch=True,
    all_branches=["release-spm.mt8678_2024_1114"],
)

all_repos_config = AllReposConfig(
    repo_configs={
        "grpower": grpower_config,
        "grt": grt_config,
        # "grt_be": grt_be_config,
        # "nebula": nebula_config,
        # "yocto": yocto_config,
        # "alps": alps_config,
    }
)
