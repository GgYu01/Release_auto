from config.schemas import RepoConfig, AllReposConfig
from utils.rich_logger import RichLogger

logger = RichLogger("repos_config")

grpower_config = RepoConfig(
    repo_name="grpower",
    repo_type="git",
    path="~/grpower",
    default_tag_prefix="grpower-",
    default_analyze_commit=True,
    default_generate_patch=True,
)

grt_config = RepoConfig(
    repo_name="grt",
    repo_type="git",
    path="~/grt",
    default_tag_prefix="grt-",
    default_analyze_commit=True,
    default_generate_patch=False,
)

grt_be_config = RepoConfig(
    repo_name="grt_be",
    repo_type="git",
    path="~/grt_be",
    default_tag_prefix="grt_be-",
    default_analyze_commit=False,
    default_generate_patch=True,
)

nebula_config = RepoConfig(
    repo_name="nebula",
    repo_type="jiri",
    path="~/grpower/workspace/nebula",
    manifest_path="~/grpower/workspace/nebula/.jiri_manifest",
    manifest_type="jiri",
    default_tag_prefix="nebula-",
    default_analyze_commit=True,
    default_generate_patch=True,
    all_branches=["master", "dev", "nebula"],
    special_branch_repos={"build":"nebula","docs":"nebula"}
)

yocto_config = RepoConfig(
    repo_name="yocto",
    repo_type="repo",
    path="~/yocto",
    manifest_path="~/yocto/.repo/manifest.xml",
    manifest_type="repo",
    default_tag_prefix="yocto-",
    default_analyze_commit=True,
    default_generate_patch=False,
    all_branches=["master", "dev"],
    special_branch_repos={"src/connectivity/gps/4.0":"dev", "src/tinysys/common":"master"}
)

alps_config = RepoConfig(
    repo_name="alps",
    repo_type="git",
    path="~/alps",
)

all_repos_config = AllReposConfig(
    repo_configs={
        "grpower": grpower_config,
        "grt": grt_config,
        "grt_be": grt_be_config,
        "nebula": nebula_config,
        "yocto": yocto_config,
        "alps": alps_config,
    }
)
