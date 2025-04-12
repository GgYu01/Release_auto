from typing import Tuple, Optional, List, Set, Dict, Any
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from config.schemas import AllReposConfig, GitRepoInfo
import re
import subprocess
from datetime import datetime

class GitTagFetcher:
    def __init__(self, command_executor: CommandExecutor, logger: Logger):
        self.command_executor: CommandExecutor = command_executor
        self.logger: Logger = logger

    def update_repo_tags(self, repos_config: AllReposConfig) -> None:
        self.logger.info("Starting repository tag update process...")
        for repo_config in repos_config.repo_configs.values():
            for git_repo_info in repo_config.git_repos:
                if git_repo_info.repo_type == "git":
                    self._process_single_repo(git_repo_info)
        self.logger.info("Repository tag update process finished.")

    def _process_single_repo(self, repo_info: GitRepoInfo) -> None:
        repo_path = repo_info.path
        local_branch = repo_info.local_branch
        tag_prefix = repo_info.tag_prefix
        remote_name = repo_info.remote_name or "origin"
        repo_name = repo_info.repo_name

        if not repo_path or not local_branch:
            self.logger.warning(
                f"Repo path or local branch missing for {repo_name}. "
                f"Skipping tag fetch."
            )
            return

        self.logger.info(
            f"Processing tags for repo '{repo_name}' at path "
            f"'{repo_path}', branch '{local_branch}', "
            f"prefix '{tag_prefix or 'None'}'."
        )

        latest_tag, next_newest_tag = self.fetch_latest_tags(
            repo_path=repo_path,
            branch_name=local_branch,
            remote_name=remote_name,
            tag_prefix=tag_prefix
        )
        repo_info.newest_version = latest_tag
        repo_info.next_newest_version = next_newest_tag
        self.logger.info(
            f"Updated versions for repo '{repo_name}': "
            f"Newest='{latest_tag}', NextNewest='{next_newest_tag}'"
        )

    def _execute_git_command(
        self,
        repo_path: str,
        command: str,
        args: List[str]
    ) -> str:
        params = {"command": command, "args": args, "cwd": repo_path}
        result = self.command_executor.execute("git_command", params)
        return result.stdout.strip()

    def _fetch_remote_tags(self, repo_path: str, remote_name: str) -> None:
        self.logger.debug(f"Fetching tags from remote '{remote_name}'...")
        fetch_args = [remote_name, "--tags", "--prune", "--force"]
        self._execute_git_command(repo_path, "fetch", fetch_args)
        self.logger.debug(f"Successfully fetched tags from {remote_name}.")

    def _get_merged_tags(self, repo_path: str, branch_name: str) -> Set[str]:
        self.logger.debug(f"Getting tags merged into branch '{branch_name}'...")
        merged_args = ["--merged", branch_name]
        output = self._execute_git_command(repo_path, "tag", merged_args)
        merged_tags_set = set(output.splitlines())
        self.logger.debug(
            f"Found {len(merged_tags_set)} tags merged into '{branch_name}'."
        )
        return merged_tags_set

    def _get_tags_with_dates(self, repo_path: str) -> str:
        self.logger.debug("Listing tags with creation dates...")
        list_args = [
            "--sort=-creatordate",
            "--format=%(refname:strip=2) %(creatordate:iso-strict)",
            "refs/tags"
        ]
        output = self._execute_git_command(repo_path, "for-each-ref", list_args)
        self.logger.debug("Successfully listed tags with dates.")
        return output

    def _parse_date(self, tag_name: str, date_str: str) -> Optional[datetime]:
        parsed_date = None
        modified_date_str = date_str
        try:
            if date_str.endswith('Z'):
                modified_date_str = date_str[:-1] + '+00:00'
            parsed_date = datetime.fromisoformat(modified_date_str)
        except ValueError as e:
            self.logger.warning(
                f"Could not parse date for tag '{tag_name}'. "
                f"Original: '{date_str}', Attempted: '{modified_date_str}'. "
                f"Error: {e}. Skipping tag."
            )
        return parsed_date

    def _extract_sequence(self, tag_name: str) -> int:
        sequence_num = 0
        try:
            sequence_part = tag_name.split('_')[-1]
            sequence_num = int(sequence_part)
        except (IndexError, ValueError):
            self.logger.warning(
                f"Could not extract sequence number from tag '{tag_name}'. "
                f"Using default 0 for sorting."
            )
        return sequence_num

    def fetch_latest_tags(
        self,
        repo_path: str,
        branch_name: str,
        remote_name: str = "origin",
        tag_prefix: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        try:
            self._fetch_remote_tags(repo_path, remote_name)

            try:
                merged_tags_set = self._get_merged_tags(repo_path, branch_name)
            except subprocess.CalledProcessError as e:
                self.logger.error(
                    f"Error getting merged tags for branch '{branch_name}' "
                    f"in {repo_path}: {e.stderr}. Cannot determine relevant tags."
                )
                return None, None
            except ValueError as e:
                self.logger.error(
                    f"Configuration error getting merged tags in {repo_path}: {e}"
                )
                return None, None

            tags_output = self._get_tags_with_dates(repo_path)
            if not tags_output:
                self.logger.warning(f"No tags found in repository {repo_path}.")
                return None, None

            valid_tags_data: List[Dict[str, Any]] = []
            tag_lines = tags_output.split("\n")

            for line in tag_lines:
                if not line: continue
                parts = line.strip().split(" ", 1)
                if len(parts) != 2:
                    self.logger.warning(f"Could not parse tag line: '{line}'")
                    continue

                tag_name, date_str = parts

                if tag_prefix and not tag_name.startswith(tag_prefix):
                    self.logger.debug(f"Skipping tag '{tag_name}': prefix mismatch.")
                    continue

                parsed_date = self._parse_date(tag_name, date_str)
                if parsed_date is None:
                    continue

                sequence_num = self._extract_sequence(tag_name)

                if tag_name not in merged_tags_set:
                    self.logger.debug(
                        f"Skipping tag '{tag_name}': not merged into "
                        f"branch '{branch_name}'."
                    )
                    continue

                self.logger.debug(f"Tag '{tag_name}' is valid.")
                valid_tags_data.append(
                    {'name': tag_name, 'date': parsed_date, 'seq': sequence_num}
                )

            if not valid_tags_data:
                self.logger.warning(
                    f"No valid tags found matching prefix '{tag_prefix}' "
                    f"and merged into '{branch_name}' in {repo_path}."
                )
                return None, None

            try:
                valid_tags_data.sort(
                    key=lambda x: (x['date'], x['seq']), reverse=True
                )
                self.logger.debug(
                    f"Sorted valid tags ({len(valid_tags_data)}): "
                    f"{[t['name'] for t in valid_tags_data]}"
                )
            except Exception as e:
                self.logger.error(f"Error sorting tags for {repo_path}: {e}")
                return None, None

            latest_tag = valid_tags_data[0]['name']
            next_newest_tag = (
                valid_tags_data[1]['name'] if len(valid_tags_data) > 1 else None
            )

            self.logger.info(
                f"Found relevant tags in {repo_path} - "
                f"Latest: {latest_tag}, Next Newest: {next_newest_tag}"
            )
            return latest_tag, next_newest_tag

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Git command failed during tag fetch for {repo_path}: {e.stderr}"
            )
            return None, None
        except ValueError as e:
            self.logger.error(
                f"Configuration error during tag fetch for {repo_path}: {e}"
            )
            return None, None
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching tags for {repo_path}: {e}",
                exc_info=True
            )
            return None, None
