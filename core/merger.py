import re
import subprocess
from typing import List, Dict, Optional
from urllib.parse import urlparse

from config.schemas import GitRepoInfo, MergeConfig
from utils.command_executor import CommandExecutor
from utils.git_utils import GitOperator # Assuming GitOperator is in git_utils
from utils.custom_logger import Logger # Assuming Logger is in custom_logger

class GerritMerger:
    def __init__(self, cmd_executor: CommandExecutor, git_operator: GitOperator, logger: Logger):
        self.cmd_executor = cmd_executor
        self.git_operator = git_operator
        self.logger = logger

    def process_merges(self, repos_to_process: List[GitRepoInfo], commits_map: Dict[str, List[str]]) -> bool:
        self.logger.info("Starting Gerrit merge process...")
        overall_success = True
        # Assuming utils.git_utils contains parse_gerrit_remote_info and extract_change_id
        from utils.git_utils import parse_gerrit_remote_info, extract_change_id

        for repo in repos_to_process:
            if not repo.merge_config or repo.merge_config.merge_mode == 'disabled':
                self.logger.debug(f"Skipping merge process for {repo.repo_name}: merge mode is disabled or not configured.")
                continue

            if not repo.remote_name:
                self.logger.error(f"Cannot process merges for {repo.repo_name}: remote_name is not configured.")
                overall_success = False
                continue

            merge_mode = repo.merge_config.merge_mode
            self.logger.info(f"Processing merges for {repo.repo_name} in '{merge_mode}' mode.")

            target_identifiers = commits_map.get(repo.repo_name, [])
            if not target_identifiers:
                self.logger.info(f"No commits/changes specified for merging in {repo.repo_name}.")
                continue

            remote_url = self.git_operator.get_remote_url(repo.repo_path, repo.remote_name)
            if not remote_url:
                self.logger.error(f"Failed to get remote URL for remote '{repo.remote_name}' in {repo.repo_name}. Skipping merges for this repo.")
                overall_success = False
                continue

            gerrit_info = parse_gerrit_remote_info(remote_url)
            if not gerrit_info or not gerrit_info.get('host'):
                self.logger.error(f"Failed to parse Gerrit info from remote URL '{remote_url}' for {repo.repo_name}. Skipping merges.")
                overall_success = False
                continue

            gerrit_host = gerrit_info['host']
            gerrit_user = gerrit_info.get('user')
            gerrit_port = gerrit_info.get('port', '29418') # Default port

            for identifier in target_identifiers:
                change_id = None
                # Crude check if identifier looks like a commit hash (SHA1) or Change-ID
                if re.fullmatch(r'I[0-9a-f]{40}', identifier, re.IGNORECASE):
                    change_id = identifier
                    self.logger.debug(f"Identifier '{identifier}' appears to be a Change-ID.")
                elif re.fullmatch(r'[0-9a-f]{7,40}', identifier, re.IGNORECASE):
                    self.logger.debug(f"Identifier '{identifier}' appears to be a commit hash. Fetching message...")
                    commit_message = self.git_operator.get_commit_message(repo.repo_path, identifier)
                    if commit_message:
                        change_id = extract_change_id(commit_message)
                        if not change_id:
                             self.logger.warning(f"Could not extract Change-ID from commit {identifier} in {repo.repo_name}.")
                    else:
                        self.logger.warning(f"Could not retrieve commit message for {identifier} in {repo.repo_name}.")
                else:
                    self.logger.warning(f"Identifier '{identifier}' in {repo.repo_name} is neither a valid Change-ID nor a commit hash. Skipping.")

                if not change_id:
                    overall_success = False # Mark as failure if we couldn't process an identifier
                    continue

                self.logger.info(f"Processing Change-ID: {change_id} for repo {repo.repo_name}")

                if merge_mode == 'auto':
                    ssh_command_parts = ["ssh"]
                    if gerrit_port:
                        ssh_command_parts.extend(["-p", gerrit_port])
                    user_host = f"{gerrit_user}@{gerrit_host}" if gerrit_user else gerrit_host
                    ssh_command_parts.extend([user_host, "gerrit", "review", "--submit", change_id])

                    command_str = " ".join(ssh_command_parts) # For logging
                    self.logger.info(f"Attempting auto-merge for {change_id} via SSH: {command_str}")

                    try:
                        # Use CommandExecutor - assuming it handles list of args
                        # Modify if CommandExecutor expects a different format
                        params = {"command": ssh_command_parts[0], "args": ssh_command_parts[1:], "cwd": repo.repo_path, "check": True}
                        result = self.cmd_executor.execute("ssh_command", params) # Use a descriptive task name
                        self.logger.info(f"Successfully submitted Change-ID {change_id} for repo {repo.repo_name}. Output:\n{result.stdout}")
                    except subprocess.CalledProcessError as e:
                        self.logger.error(f"Failed to submit Change-ID {change_id} for repo {repo.repo_name}. Command failed: {command_str}\nError: {e.stderr}")
                        overall_success = False
                    except Exception as e:
                         self.logger.error(f"An unexpected error occurred during SSH command execution for {change_id} in {repo.repo_name}: {e}")
                         overall_success = False

                elif merge_mode == 'manual':
                    self.logger.info(f"MANUAL MERGE REQUIRED for Change-ID {change_id} in repo {repo.repo_name} on Gerrit host {gerrit_host}.")
                    # No command execution in manual mode

        self.logger.info(f"Gerrit merge process finished. Overall success: {overall_success}")
        return overall_success