from dataclasses import replace
from typing import Optional, List, Dict
from config.schemas import GitRepoInfo, RepoConfig, AllReposConfig
from utils.rich_logger import Logger

logger = Logger("repo_updater")

class RepoPropertyUpdater:
    def __init__(self, all_repos_config: AllReposConfig):
        self._config = all_repos_config
        
    def _get_repo_config(self, parent_name: str) -> Optional[RepoConfig]:
        return self._config.repo_configs.get(parent_name)
        
    def _update_git_repo_properties(self, git_repo: GitRepoInfo, repo_config: RepoConfig) -> GitRepoInfo:
        branch_info = repo_config.all_branches
        if git_repo.repo_name in repo_config.special_branch_repos:
            branch_info = repo_config.special_branch_repos[git_repo.repo_name]
            
        return replace(
            git_repo,
            tag_prefix=repo_config.default_tag_prefix,
            analyze_commit=repo_config.default_analyze_commit,
            generate_patch=repo_config.default_generate_patch,
            branch_info=branch_info
        )

    def update_all_repos(self) -> None:
        for repo_config in self._config.repo_configs.values():
            try:
                updated_repos = []
                for git_repo in repo_config.git_repos:
                    parent_config = self._get_repo_config(git_repo.repo_parent)
                    if parent_config:
                        updated_repo = self._update_git_repo_properties(git_repo, parent_config)
                        updated_repos.append(updated_repo)
                    else:
                        updated_repos.append(git_repo)
                repo_config.git_repos = updated_repos
            except Exception as e:
                logger.error(f"Error updating repos for {repo_config.repo_name}: {e}")
