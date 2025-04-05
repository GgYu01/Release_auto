from typing import Tuple, Optional, List
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from config.schemas import AllReposConfig
import re
import subprocess
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
                    remote_name = git_repo_info.remote_name or "origin"

                    if repo_path and local_branch:
                        latest_tag, next_newest_tag = self.fetch_latest_tags(
                            repo_path=repo_path,
                            branch_name=local_branch,
                            remote_name=remote_name,
                            tag_prefix=tag_prefix
                        )
                        git_repo_info.newest_version = latest_tag
                        git_repo_info.next_newest_version = next_newest_tag
                        self.logger.info(f"Updated versions for repo: {git_repo_info.repo_name}, newest: {latest_tag}, next_newest: {next_newest_tag}")
                    else:
                        self.logger.warning(f"Repo path or local branch missing for {git_repo_info.repo_name}, skipping tag fetch")
        self.logger.info("Repository tags updated")

    def fetch_latest_tags(self, repo_path: str, branch_name: str, remote_name: str = "origin", tag_prefix: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        try:
            self.logger.info(f"Fetching tags for repo at {repo_path} on branch {branch_name} from remote {remote_name}")

            try:
                fetch_params = {
                    "command": "fetch",
                    "args": [remote_name, "--tags", "--prune"],
                    "cwd": repo_path
                }
                self.command_executor.execute("git_command", fetch_params)
                self.logger.info(f"Successfully fetched tags from {remote_name} for {repo_path}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Error executing git fetch for tags in {repo_path}: {e.stderr}")
                return None, None
            except ValueError as e:
                 self.logger.error(f"Configuration error during git fetch for tags in {repo_path}: {e}")
                 return None, None

            try:
                list_tags_params = {
                    "command": "for-each-ref",
                    "args": [
                        "--sort=-creatordate",
                        "--format=%(refname:strip=2) %(creatordate:iso-strict)",
                        "refs/tags"
                    ],
                    "cwd": repo_path
                }
                result = self.command_executor.execute("git_command", list_tags_params)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Error executing git for-each-ref in {repo_path}: {e.stderr}")
                return None, None
            except ValueError as e:
                 self.logger.error(f"Configuration error during git for-each-ref in {repo_path}: {e}")
                 return None, None

            output = result.stdout.strip()
            if not output:
                self.logger.warning(f"No tags found in repository {repo_path} after fetch")
                return None, None

            tags_with_dates = self._parse_tag_dates(output.split("\n"))

            if tag_prefix:
                tags_with_dates = [tag for tag in tags_with_dates if tag[0].startswith(tag_prefix)]
                if not tags_with_dates:
                     self.logger.warning(f"No tags found with prefix '{tag_prefix}' in {repo_path}")
                     return None, None

            sorted_tags = tags_with_dates 

            if not sorted_tags:
                self.logger.warning(f"Tag list empty after parsing/filtering for {repo_path}")
                return None, None

            latest_tag = sorted_tags[0][0]
            penultimate_tag = sorted_tags[1][0] if len(sorted_tags) > 1 else None

            self.logger.info(f"Found tags in {repo_path} - Latest: {latest_tag}, Penultimate: {penultimate_tag}")
            # The original request asked for (latest, next_newest) tuple return.
            # Let's adjust the return to match the variable names used earlier in update_repo_tags
            # newest_version = latest_tag
            # next_newest_version = penultimate_tag
            # return newest_version, next_newest_version
            # But the function signature return was defined as Tuple[Optional[str], Optional[str]]
            # And the call site assigned latest_tag, next_newest_tag = ...
            # This implies the function should return (latest, next_newest) based on call site.
            # However, the logic inside sets latest_tag=sorted[0] and penultimate_tag=sorted[1]
            # Let's return them in the order expected by the call site: latest, then the one before it.
            return latest_tag, penultimate_tag

        except Exception as e:
            self.logger.error(f"Unexpected error fetching tags for {repo_path}: {e}", exc_info=True)
            return None, None

    def _parse_tag_dates(self, tag_lines: List[str]) -> List[Tuple[str, datetime]]:
        tag_dates = []
        for line in tag_lines:
            if not line: continue
            parts = line.rsplit(' ', 1)
            if len(parts) == 2:
                tag_name = parts[0]
                try:
                    date_str = parts[1].replace("Z", "+00:00")
                    if ":" == date_str[-3:-2]:
                        date_str = date_str[:-3] + date_str[-2:]
                    tag_date = datetime.fromisoformat(date_str)
                    tag_dates.append((tag_name, tag_date))
                except ValueError as e:
                    self.logger.warning(f"Could not parse date for tag '{tag_name}': {parts[1]} - Error: {e}")
            else:
                self.logger.warning(f"Could not parse tag line: {line}")
        return tag_dates