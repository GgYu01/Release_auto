import datetime
import re
import pytz  # Library dependency: pytz
from config.repos_config import all_repos_config
from config.tagging_config import TaggingConfig
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from utils.tag_utils import parse_version_identifier, generate_next_version_identifier

class Tagger:
    def __init__(self, tagging_config: TaggingConfig, command_executor: CommandExecutor):
        self.tagging_config = tagging_config
        self.command_executor = command_executor
        self.logger = Logger(name="Tagger")
        self.grt_repo_name = tagging_config.grt_repo_name
        self.timezone_str = tagging_config.timezone

    def get_current_time_in_config_timezone(self):
        tz = pytz.timezone(self.timezone_str)
        return datetime.datetime.now(tz)

    def get_latest_tag_from_grt(self):
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
            return latest_tag
        except Exception as e:
            self.logger.warning(f"Failed to get latest tag from GRT repo: {e}")
            return None

    def get_existing_tags(self, repo_path: str, tag_prefix: str) -> list:
        """Get all existing tags that match the given prefix."""
        command_params = {
            "command": "tag",
            "args": ["--list", f"{tag_prefix}*"],
            "cwd": repo_path
        }
        try:
            result = self.command_executor.execute("git_command", command_params)
            return result.stdout.strip().splitlines()
        except Exception as e:
            self.logger.warning(f"Failed to list tags: {e}")
            return []

    def extract_version_parts(self, tag_name: str, tag_prefix: str) -> tuple:
        """Extract date and sequence number from a tag name."""
        version_identifier = tag_name.replace(tag_prefix, "", 1)
        match = re.match(r"(\d{4}_\d{4})_(\d{2})", version_identifier)
        if match:
            date_part = match.group(1)
            sequence_number = int(match.group(2))
            return date_part, sequence_number
        return None, None

    def find_latest_sequence_number(self, tags: list, tag_prefix: str, current_date_str: str) -> int:
        """Find the latest sequence number for tags with the given date."""
        latest_sequence = 0
        for tag in tags:
            date_part, sequence_number = self.extract_version_parts(tag, tag_prefix)
            if date_part == current_date_str:
                latest_sequence = max(latest_sequence, sequence_number)
        return latest_sequence

    def generate_version_identifier(self, tag_prefix: str, repo_path: str) -> str:
        """Generate a new version identifier, handling existing tags."""
        manual_version_identifier = self.tagging_config.manual_version_identifier
        if manual_version_identifier:
            self.logger.info(f"Using manually configured version identifier: {manual_version_identifier}")
            return manual_version_identifier

        current_time = self.get_current_time_in_config_timezone()
        current_date_str = current_time.strftime("%Y_%m%d")
        
        # Get existing tags and find the latest sequence number
        existing_tags = self.get_existing_tags(repo_path, tag_prefix)
        latest_sequence = self.find_latest_sequence_number(existing_tags, tag_prefix, current_date_str)
        
        # Generate the next sequence number
        next_sequence = latest_sequence + 1
        return f"{current_date_str}_{next_sequence:02d}"

    def tag_repositories(self):
        """Tag repositories with proper version handling."""
        for repo_config in all_repos_config.repo_configs.values():
            for git_repo_info in repo_config.git_repos:
                tag_prefix = git_repo_info.tag_prefix
                if not tag_prefix:
                    self.logger.warning(f"No tag_prefix configured for repo: {git_repo_info.repo_name}, skipping tagging.")
                    continue

                version_identifier = self.generate_version_identifier(tag_prefix, git_repo_info.repo_path)
                tag_name = f"{tag_prefix}{version_identifier}"

                self.logger.info(f"Tagging repository: {git_repo_info.repo_name} with tag: {tag_name}")
                command_params = {
                    "command": "tag",
                    "args": [tag_name],
                    "cwd": git_repo_info.repo_path
                }
                try:
                    self.command_executor.execute("git_command", command_params)
                    self.logger.info(f"Successfully tagged repository: {git_repo_info.repo_name} with tag: {tag_name}")
                except Exception as e:
                    self.logger.error(f"Failed to tag repository: {git_repo_info.repo_name} with tag: {tag_name}, error: {e}")
