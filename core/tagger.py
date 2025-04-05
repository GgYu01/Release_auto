import datetime
from typing import Optional, List, Tuple
import re
import pytz
from config.repos_config import all_repos_config
from config.tagging_config import TaggingConfig
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from utils.tag_utils import (
    parse_version_identifier,
    generate_next_version_identifier,
    InvalidVersionIdentifierFormatError
)

class Tagger:
    def __init__(self, tagging_config: TaggingConfig, command_executor: CommandExecutor):
        self.tagging_config = tagging_config
        self.command_executor = command_executor
        self.logger = Logger(name="Tagger")
        self.grt_repo_name = tagging_config.grt_repo_name
        self.timezone_str = tagging_config.timezone

    def get_current_time_in_config_timezone(self) -> datetime.datetime:
        tz = pytz.timezone(self.timezone_str)
        return datetime.datetime.now(tz)

    def get_latest_tag_from_grt(self) -> Optional[str]:
        grt_repo_config = all_repos_config.repo_configs.get(self.grt_repo_name)
        if not grt_repo_config:
            self.logger.error(f"GRT repo '{self.grt_repo_name}' not found in config.")
            return None

        command_params = {
            "command": "describe",
            "args": ["--tags", "--abbrev=0"],
            "cwd": grt_repo_config.path 
        }
        try:
            result = self.command_executor.execute("git_command", command_params)
            latest_tag = result.stdout.strip()
            self.logger.debug(f"Retrieved latest tag from GRT: {latest_tag}")
            return latest_tag
        except Exception as e:
            self.logger.warning(f"Failed to get latest tag from GRT repo: {e}")
            return None

    def get_existing_tags(self, repo_path: str, tag_prefix: str) -> List[str]:
        command_params = {
            "command": "tag",
            "args": ["--list", f"{tag_prefix}*"],
            "cwd": repo_path
        }
        try:
            result = self.command_executor.execute("git_command", command_params)
            tags = result.stdout.strip().splitlines()
            self.logger.debug(f"Found {len(tags)} existing tags")
            return tags
        except Exception as e:
            self.logger.warning(f"Failed to list tags: {e}")
            return []

    def _extract_version_parts(
        self, tag_name: str, tag_prefix: str
    ) -> Tuple[Optional[str], Optional[int]]:
        version_identifier = tag_name.replace(tag_prefix, "", 1)
        try:
            parsed = parse_version_identifier(version_identifier)
            return (
                parsed["date"].strftime("%Y_%m%d"),
                parsed["counter"]
            )
        except InvalidVersionIdentifierFormatError:
            self.logger.debug(
                f"Failed to parse version identifier: {version_identifier}")
            return None, None

    def _find_latest_sequence_number(
        self, tags: List[str], tag_prefix: str, current_date_str: str
    ) -> int:
        latest_sequence = 0
        for tag in tags:
            date_part, sequence_number = self._extract_version_parts(tag, tag_prefix)
            if date_part == current_date_str and sequence_number is not None:
                latest_sequence = max(latest_sequence, sequence_number)
        self.logger.debug(f"Latest sequence number found: {latest_sequence}")
        return latest_sequence

    def generate_version_identifier(self, tag_prefix: str, repo_path: str) -> str:
        manual_version_identifier = self.tagging_config.manual_version_identifier
        if manual_version_identifier:
            self.logger.info(
                f"Using manual version identifier: {manual_version_identifier}")
            return manual_version_identifier

        current_time = self.get_current_time_in_config_timezone()
        existing_tags = self.get_existing_tags(repo_path, tag_prefix)
        current_date_str = current_time.strftime("%Y_%m%d")
        latest_sequence = self._find_latest_sequence_number(
            existing_tags, tag_prefix, current_date_str)
        
        version_identifier = generate_next_version_identifier(
            current_time, latest_sequence)
        self.logger.info(f"Generated version identifier: {version_identifier}")
        return version_identifier

    def tag_repositories(self) -> None:
        self.logger.info("Starting repository tagging process")
        for repo_config in all_repos_config.repo_configs.values():
            for git_repo_info in repo_config.git_repos:
                tag_prefix = git_repo_info.tag_prefix
                if not tag_prefix:
                    self.logger.warning(
                        f"No tag_prefix for repo: {git_repo_info.repo_name}")
                    continue

                version_identifier = self.generate_version_identifier(
                    tag_prefix, git_repo_info.repo_path)
                tag_name = f"{tag_prefix}{version_identifier}"

                command_params = {
                    "command": "tag",
                    "args": [tag_name],
                    "cwd": git_repo_info.repo_path
                }
                try:
                    self.command_executor.execute("git_command", command_params)
                    self.logger.info(
                        f"Tagged {git_repo_info.repo_name} with {tag_name}")
                except Exception as e:
                    self.logger.error(
                        f"Failed to tag {git_repo_info.repo_name}: {e}")
        self.logger.info("Repository tagging process completed")
