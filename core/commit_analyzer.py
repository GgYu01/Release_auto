from typing import List, Dict
from utils.git_utils import GitOperator
from utils.custom_logger import Logger
from config.schemas import AllReposConfig, GitRepoInfo
import traceback

class CommitAnalyzer:
    def __init__(self, git_operator: GitOperator, logger: Logger):
        if not git_operator:
            raise ValueError("GitOperator instance is required")
        if not logger:
            raise ValueError("Logger instance is required")
        self.git_operator = git_operator
        self.logger = logger

    def analyze_all_repositories(self, all_repos_config: AllReposConfig) -> None:
        self.logger.info("Starting commit analysis for all configured repositories...")

        for repo_info in all_repos_config.all_git_repos():
            try:
                self.logger.debug(f"Checking commit analysis eligibility for repo: {repo_info.repo_name}")

                if not repo_info.analyze_commit:
                    self.logger.debug(f"Skipping commit analysis for {repo_info.repo_name}: analyze_commit is False.")
                    continue

                if not repo_info.repo_path:
                     self.logger.warning(f"Skipping commit analysis for {repo_info.repo_name}: repo_path is not defined.")
                     continue

                if not repo_info.newest_version or not repo_info.next_newest_version:
                    self.logger.info(f"Skipping commit analysis for {repo_info.repo_name}: Missing newest_version ('{repo_info.newest_version}') or next_newest_version ('{repo_info.next_newest_version}'). Tags might not have been fetched or found.")
                    continue

                start_ref = repo_info.next_newest_version
                end_ref = repo_info.newest_version

                self.logger.info(f"Analyzing commits for {repo_info.repo_name} between tags: {start_ref} -> {end_ref}")

                commit_details: List[Dict[str, str]] = self.git_operator.get_commits_between(
                    repository_path=repo_info.repo_path,
                    start_ref=start_ref,
                    end_ref=end_ref
                )

                repo_info.commit_details = commit_details
                self.logger.info(f"Found {len(commit_details)} commits for {repo_info.repo_name} between {start_ref} and {end_ref}.")

            except Exception as e:
                self.logger.error(f"Error during commit analysis for repository {repo_info.repo_name}: {e}")
                self.logger.debug(traceback.format_exc()) # Log full traceback for debugging
                # Continue to the next repository even if one fails

        self.logger.info("Finished commit analysis for all repositories.")