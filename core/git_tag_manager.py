from typing import Tuple, Optional, List
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from config.schemas import AllReposConfig
import re
from datetime import datetime

class GitTagFetcher:
    def __init__(self, command_executor: CommandExecutor, logger: Logger):
        self.command_executor = command_executor
        self.logger = logger

    def update_repo_tags(self, repos_config: AllReposConfig):
        self.logger.info("Fetching and updating repository tags...")
        for repo_config in repos_config.repo_configs.values():
            for git_repo_info in repo_config.git_repos:
                if git_repo_info.repo_type == "git":
                    repo_path = git_repo_info.path
                    local_branch = git_repo_info.local_branch
                    tag_prefix = git_repo_info.tag_prefix

                    if repo_path and local_branch:
                        latest_tag, next_newest_tag = self.fetch_latest_tags(
                            repo_path=repo_path,
                            branch_name=local_branch,
                            tag_prefix=tag_prefix
                        )
                        git_repo_info.newest_version = latest_tag
                        git_repo_info.next_newest_version = next_newest_tag
                        self.logger.info(f"Updated versions for repo: {git_repo_info.repo_name}, newest: {latest_tag}, next_newest: {next_newest_tag}")
                    else:
                        self.logger.warning(f"Repo path or local branch missing for {git_repo_info.repo_name}, skipping tag fetch")
        self.logger.info("Repository tags updated")

    def fetch_latest_tags(self, repo_path: str, branch_name: str, tag_prefix: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        try:
            self.logger.info(f"Fetching tags for repo at {repo_path} on branch {branch_name}")
            
            git_cmd = f"cd {repo_path} && git for-each-ref --sort=-creatordate --format '%(refname:strip=2) %(creatordate:iso-strict)' refs/tags"
            result = self.command_executor.run_command(git_cmd)
            
            if not result or not result.strip():
                self.logger.warning(f"No tags found in repository {repo_path}")
                return None, None
            
            tags_with_dates = self._parse_tag_dates(result.strip().split("\n"))
            sorted_tags = self._validate_tag_chronology(tags_with_dates)
            
            if not sorted_tags:
                return None, None
            
            latest_tag = sorted_tags[0][0]  # Latest tag
            penultimate_tag = sorted_tags[1][0] if len(sorted_tags) > 1 else None  # Penultimate tag
            
            self.logger.info(f"Found tags - penultimate: {penultimate_tag}, latest: {latest_tag}")
            return penultimate_tag, latest_tag
            
        except Exception as e:
            self.logger.error(f"Error fetching tags: {e}")
            return None, None 

    def _parse_tag_dates(self, tag_lines: List[str]) -> List[Tuple[str, datetime]]:
        tag_dates = []
        for line in tag_lines:
            parts = line.rsplit(' ', 1)
            if len(parts) == 2:
                tag_name = parts[0]
                tag_date = datetime.fromisoformat(parts[1])
                tag_dates.append((tag_name, tag_date))
        return tag_dates

    def _validate_tag_chronology(self, tags_with_dates: List[Tuple[str, datetime]]) -> List[Tuple[str, datetime]]:
        # Sort by commit date and then by tag creation time
        tags_with_dates.sort(key=lambda x: (x[1]))  # Sort by date
        return tags_with_dates 