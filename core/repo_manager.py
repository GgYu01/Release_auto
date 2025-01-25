import xml.etree.ElementTree as ET
from config.schemas import GitRepoInfo, RepoConfig, AllReposConfig
from utils.file_utils import construct_path
from utils.custom_logger import Logger
from core.repo_updater import RepoPropertyUpdater

logger = Logger("repo_manager")

class RepoManager:

    def __init__(self, all_repos_config: AllReposConfig):
        self.all_repos_config = all_repos_config
        self._repo_updater = RepoPropertyUpdater(all_repos_config)

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
                    remote_name=None,
                    remote_branch=None,
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
                    remote_name=None,
                    remote_branch=None,
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
            
            self._repo_updater.update_all_repos()
        except Exception as e:
            logger.error(f"Error initializing GitRepoInfo: {e}")
