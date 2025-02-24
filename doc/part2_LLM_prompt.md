
请根据以下描述和要求，在 `~/Release_auto` 项目中，使用 Python 语言生成代码：

功能：根据 `config/repos_config.py` 文件中 `all_repos_config` 的配置信息，遍历并更新一个大型数据结构中所有 Git 仓库对象的属性。

已有的代码如下，目前需要你增加功能。

nebula@ab2c1af07fa4:~/Release_auto $ tree
.
├── assisted_workflow.md
├── code_structure.md
├── config
│   ├── config_loader.py
│   ├── default_config.py
│   ├── global_config.py
│   ├── init_config.py
│   ├── __init__.py
│   ├── logging_config.py
│   ├── repos_config.py
│   └── schemas.py
├── core
│   ├── builder.py
│   ├── commit_analyzer.py
│   ├── __init__.py
│   ├── merger.py
│   ├── patch_generator.py
│   ├── repo_manager.py
│   ├── snapshot_manager.py
│   └── tagger.py
├── deep_think.md
├── Design_for_Base.md
├── part1_LLM_generate_code.md
├── part1.md
├── part2.md
├── release.py
├── user_story_split.md
└── utils
    ├── excel_utils.py
    ├── file_utils.py
    ├── git_utils.py
    ├── __init__.py
    ├── rich_logger.py
    └── tag_utils.py

3 directories, 31 files

nebula@ab2c1af07fa4:~/Release_auto $ tail -n +1 config/repos_config.py config/schemas.py core/repo_manager.py release.py 
==> config/repos_config.py <==
from config.schemas import RepoConfig, AllReposConfig
from utils.rich_logger import RichLogger

logger = RichLogger("repos_config")

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
        "grt_be": grt_be_config,
        "nebula": nebula_config,
        "yocto": yocto_config,
        "alps": alps_config,
    }
)

==> config/schemas.py <==
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class GitRepoInfo:
    repo_name: str
    repo_parent: str
    path: str
    repo_type: str
    tag_prefix: Optional[str] = None
    remote_name: Optional[str] = None
    remote_branch: Optional[str] = None
    parent_repo: Optional[str] = None
    commit_analyses: List[Dict] = field(default_factory=list)
    newest_version: Optional[str] = None
    next_newest_version: Optional[str] = None
    analyze_commit: bool = False
    generate_patch: bool = False
    branch_info: Optional[str] = None
    push_template: Optional[str] = None

@dataclass
class RepoConfig:
    repo_name: str
    repo_type: str
    path: str
    git_repos: List[GitRepoInfo] = field(default_factory=list)
    manifest_path: Optional[str] = None
    default_tag_prefix: Optional[str] = None
    parent_repo: Optional[str] = None
    manifest_type: Optional[str] = None
    default_analyze_commit: bool = False
    default_generate_patch: bool = False
    all_branches: List[str] = field(default_factory=list)
    special_branch_repos: Dict[str, str] = field(default_factory=dict)

@dataclass
class AllReposConfig:
    repo_configs: Dict[str, RepoConfig] = field(default_factory=dict)

    def all_git_repos(self):
        for repo_config in self.repo_configs.values():
            for git_repo in repo_config.git_repos:
                yield git_repo

==> core/repo_manager.py <==
import xml.etree.ElementTree as ET
from config.schemas import GitRepoInfo, RepoConfig, AllReposConfig
from utils.file_utils import construct_path
from utils.rich_logger import RichLogger

logger = RichLogger("repo_manager")

class RepoManager:

    def __init__(self, all_repos_config: AllReposConfig):
        self.all_repos_config = all_repos_config

    def parse_manifest(self, repo_config: RepoConfig):
        try:
            if repo_config.manifest_path:
                if repo_config.repo_type == "jiri":
                    self._parse_jiri_manifest(repo_config)
                elif repo_config.repo_type == "repo":
                    self._parse_repo_manifest(repo_config)
        except Exception as e:
            logger.error(f"Error parsing manifest for {repo_config.repo_name}: {e}")

    def _parse_jiri_manifest(self, repo_config: RepoConfig):
        try:
            tree = ET.parse(repo_config.manifest_path)
            root = tree.getroot()
            for project in root.findall("projects/project"):
                repo_name = project.get("name")
                repo_path = construct_path(repo_config.path, project.get("path"))

                git_repo_info = GitRepoInfo(
                    repo_name=repo_name,
                    repo_parent=repo_config.repo_name,
                    path=repo_path,
                    repo_type="git",
                    tag_prefix=repo_config.default_tag_prefix,
                    remote_name=project.get("remote"),
                    remote_branch=project.get("remotebranch"),
                    parent_repo=repo_config.repo_name,
                    analyze_commit=repo_config.default_analyze_commit,
                    generate_patch=repo_config.default_generate_patch,
                )
                if repo_name in repo_config.special_branch_repos:
                    git_repo_info.remote_branch = repo_config.special_branch_repos[repo_name]

                repo_config.git_repos.append(git_repo_info)
                logger.info(f"Added GitRepoInfo for {repo_name} from jiri manifest")
        except Exception as e:
            logger.error(f"Error parsing jiri manifest for {repo_config.repo_name}: {e}")

    def _parse_repo_manifest(self, repo_config: RepoConfig):
        try:
            tree = ET.parse(repo_config.manifest_path)
            root = tree.getroot()
            remotes = {}

            for remote in root.findall("remote"):
              remotes[remote.get("name")] = remote.get("fetch")
            
            for project in root.findall("project"):
                repo_name = project.get("name")
                repo_path = construct_path(repo_config.path, project.get("path"))
                remote_name = project.get("remote")

                git_repo_info = GitRepoInfo(
                    repo_name=repo_name,
                    repo_parent=repo_config.repo_name,
                    path=repo_path,
                    repo_type="git",
                    tag_prefix=repo_config.default_tag_prefix,
                    remote_name=remote_name,
                    remote_branch=project.get("revision"),
                    parent_repo=repo_config.repo_name,
                    analyze_commit=repo_config.default_analyze_commit,
                    generate_patch=repo_config.default_generate_patch,
                )
                if repo_name in repo_config.special_branch_repos:
                    git_repo_info.remote_branch = repo_config.special_branch_repos[repo_name]

                repo_config.git_repos.append(git_repo_info)
                logger.info(f"Added GitRepoInfo for {repo_name} from repo manifest")
        except Exception as e:
            logger.error(f"Error parsing repo manifest for {repo_config.repo_name}: {e}")

    def initialize_git_repos(self):
        try:
            for repo_config in self.all_repos_config.repo_configs.values():
                if repo_config.repo_type == "git":
                    git_repo_info = GitRepoInfo(
                        repo_name=repo_config.repo_name,
                        repo_parent=repo_config.repo_name,
                        path=repo_config.path,
                        repo_type="git",
                        tag_prefix=repo_config.default_tag_prefix,
                        parent_repo=repo_config.repo_name,
                        analyze_commit=repo_config.default_analyze_commit,
                        generate_patch=repo_config.default_generate_patch,
                    )
                    repo_config.git_repos.append(git_repo_info)
                    logger.info(f"Added GitRepoInfo for {repo_config.repo_name}")
                elif repo_config.repo_type in ["jiri", "repo"]:
                    self.parse_manifest(repo_config)
        except Exception as e:
            logger.error(f"Error initializing GitRepoInfo: {e}")

==> release.py <==
from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.rich_logger import RichLogger

logger = RichLogger("release")

def main():
    try:
        repo_manager = RepoManager(all_repos_config)
        repo_manager.initialize_git_repos()

        for git_repo in all_repos_config.all_git_repos():
            logger.info(f"Git Repo Name: {git_repo.repo_name}")
            logger.info(f"Git Repo Path: {git_repo.path}")
            logger.info(f"Git Repo Type: {git_repo.repo_type}")
            logger.info(f"Parent Repo: {git_repo.parent_repo}")
            logger.info("-" * 20)
        
        logger.save_html()

    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

if __name__ == "__main__":
    main()

具体步骤：

1. 遍历大型数据结构中的每个 Git 仓库对象。
2. 对于每个对象，获取其 `repo_parent` 属性值。
3. 使用 `repo_parent` 的值作为键，在 `all_repos_config.repo_configs` 中查找对应的 `RepoConfig` 对象。
4. 如果找到对应的 `RepoConfig` 对象，则进行以下属性更新：
    *   `tag_prefix` 设置为 `RepoConfig.default_tag_prefix`。
    *   `analyze_commit` 设置为 `RepoConfig.default_analyze_commit`。
    *   `generate_patch` 设置为 `RepoConfig.default_generate_patch`。
    *   `branch_info` 设置为 `RepoConfig.all_branches`。
    *   如果当前 `RepoConfig` 对象有名为`special_branch_repos`的成员变量，并且当前 Git 仓库的名称 (即 `GitRepoInfo.repo_name`) 存在于 `RepoConfig.special_branch_repos` 的键 (key) 中，则使用 `RepoConfig.special_branch_repos` 中对应的值来更新 `GitRepoInfo.branch_info`。
    *   保持 `repo_name` 和 `path` 属性不变。
5. 将更新后的对象写回大型数据结构。

请注意：

*   确保代码清晰、简洁、易于理解，并添加必要的注释。
*   根据项目实际情况，合理安排代码在项目中的位置。
*   请只生成 python 代码，不要包含任何其他文本说明。

我对代码要求如下：
1. 代码采用高度模块化设计，支持后续扩展和维护。
2. 不考虑安全性、性能和资源占用，只注重可配置性和灵活性。
3. 功能尽量以Python库或第三方包实现，不使用Bash命令。
4. 使用完整的异常处理机制确保运行稳定。
5. 配置系统应全面、可独立管理，并能在不修改代码的情况下灵活控制功能。
6. 禁止在代码中包含注释或docstring。
7. 模块化结构需利用Python高级特性（装饰器、类、插件架构、扩展模块、上下文管理器、依赖注入等）。
8. 遵循最佳实践，确保代码清晰、简洁、健壮，且具备灵活的包结构。
