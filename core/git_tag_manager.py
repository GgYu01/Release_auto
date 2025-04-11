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
            self.logger.info(f"Fetching tags for repo at {repo_path} on branch {branch_name} from remote {remote_name} with prefix '{tag_prefix or 'None'}'")

            # Step 1: Fetch tags from remote
            try:
                fetch_params = {
                    "command": "fetch",
                    "args": [remote_name, "--tags", "--prune", "--force"], # Added --force for robustness
                    "cwd": repo_path
                }
                self.command_executor.execute("git_command", fetch_params)
                self.logger.debug(f"Successfully fetched tags from {remote_name} for {repo_path}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Error executing git fetch for tags in {repo_path}: {e.stderr}")
                return None, None
            except ValueError as e:
                 self.logger.error(f"Configuration error during git fetch for tags in {repo_path}: {e}")
                 return None, None

            # Step 2: List tags with dates
            try:
                # Get tags with strict ISO date format
                list_tags_params = {
                    "command": "for-each-ref",
                    "args": [
                        "--sort=-creatordate", # Git sorts primarily by date
                        "--format=%(refname:strip=2) %(creatordate:iso-strict)", # tag_name YYYY-MM-DDTHH:MM:SSZ
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

            # Step 3: Parse, Filter, and Extract Sequence Number
            valid_tags_data = []
            tag_lines = output.split("\n")

            for line in tag_lines:
                if not line: continue
                parts = line.strip().split(" ", 1) # Split only on the first space

                if len(parts) == 2:
                    tag_name, date_str = parts

                    # Filter by prefix FIRST
                    if tag_prefix and not tag_name.startswith(tag_prefix):
                        self.logger.debug(f"Skipping tag '{tag_name}' due to prefix mismatch (Expected: '{tag_prefix}')")
                        continue

                    # Robust Date Parsing
                    parsed_date = None
                    modified_date_str = date_str # Keep original for logging
                    try:
                        if date_str.endswith('Z'):
                            modified_date_str = date_str[:-1] + '+00:00'
                            self.logger.debug(f"Modified date string for tag '{tag_name}': '{date_str}' -> '{modified_date_str}'")
                        # Now parse the potentially modified string
                        parsed_date = datetime.fromisoformat(modified_date_str)
                        self.logger.debug(f"Successfully parsed date for tag '{tag_name}': {parsed_date}")
                    except ValueError as e:
                        self.logger.warning(f"Could not parse date for tag '{tag_name}'. Original: '{date_str}', Attempted: '{modified_date_str}'. Error: {e}. Skipping tag.")
                        continue # Skip this tag if date parsing fails

                    # Sequence Number Extraction (Example: 'prefix_YYYY_MMDD_NN')
                    sequence_num = 0 # Default if extraction fails
                    try:
                        # Attempt to extract the last part after '_' as sequence number
                        sequence_part = tag_name.split('_')[-1]
                        sequence_num = int(sequence_part)
                        self.logger.debug(f"Extracted sequence number {sequence_num} for tag '{tag_name}'")
                    except (IndexError, ValueError):
                         self.logger.warning(f"Could not extract sequence number from tag '{tag_name}'. Using default 0 for sorting.")
                         # Continue processing the tag, but it will sort with sequence 0

                    # Store valid tag data for sorting
                    valid_tags_data.append({'name': tag_name, 'date': parsed_date, 'seq': sequence_num})
                else:
                    self.logger.warning(f"Could not parse tag line format: '{line}'")


            # Step 4: Sort by Date (desc) and Sequence (desc)
            if not valid_tags_data:
                self.logger.warning(f"No valid tags found matching prefix '{tag_prefix}' after parsing in {repo_path}")
                return None, None

            try:
                # Sort using a lambda function for the two keys
                valid_tags_data.sort(key=lambda x: (x['date'], x['seq']), reverse=True)
                self.logger.debug(f"Sorted tags ({len(valid_tags_data)}): {[t['name'] for t in valid_tags_data]}")
            except Exception as e:
                 self.logger.error(f"Error sorting tags for {repo_path}: {e}", exc_info=True)
                 return None, None # Cannot proceed if sorting fails

            # Step 5: Select Latest and Next Newest
            latest_tag = valid_tags_data[0]['name']
            next_newest_tag = valid_tags_data[1]['name'] if len(valid_tags_data) > 1 else None

            self.logger.info(f"Found tags in {repo_path} matching prefix '{tag_prefix}' - Latest: {latest_tag}, Next Newest: {next_newest_tag}")
            return latest_tag, next_newest_tag

        except Exception as e:
            self.logger.error(f"Unexpected error fetching tags for {repo_path}: {e}", exc_info=True)
            return None, None

# Removed _parse_tag_dates method as logic is now integrated into fetch_latest_tags