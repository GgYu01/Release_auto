import os
import traceback
from typing import List, Dict
from utils.git_utils import GitOperator
from utils.custom_logger import Logger
from config.schemas import AllReposConfig, GitRepoInfo
from utils.tag_utils import construct_tag

class CommitAnalyzer:
    def __init__(self, git_operator: GitOperator, logger: Logger) -> None:
        if not git_operator:
            raise ValueError("GitOperator instance is required")
        if not logger:
            raise ValueError("Logger instance is required")
        self.git_operator: GitOperator = git_operator
        self.logger: Logger = logger

    def analyze_all_repositories(
        self,
        all_repos_config: AllReposConfig,
        newest_version_identifier: str,
        next_newest_version_identifier: str
    ) -> None:
        self.logger.info("Starting commit analysis using centralized version identifiers...")
        self.logger.info(f"Using newest identifier: '{newest_version_identifier}', next newest identifier: '{next_newest_version_identifier}'")

        for repo_info in all_repos_config.all_git_repos():
            try:
                self.logger.debug(f"Checking commit analysis eligibility for repo: {repo_info.repo_name}")

                if not repo_info.analyze_commit:
                    self.logger.debug(f"Skipping commit analysis for {repo_info.repo_name}: analyze_commit is False.")
                    continue

                if not repo_info.repo_path:
                    self.logger.warning(f"Skipping commit analysis for {repo_info.repo_name}: repo_path is not defined.")
                    continue

                if not os.path.exists(repo_info.repo_path):
                    self.logger.warning(f"Skipping commit analysis for {repo_info.repo_name}: Repository path '{repo_info.repo_path}' does not exist.")
                    continue

                self.logger.debug(f"Constructing tags for {repo_info.repo_name} using its prefix '{repo_info.tag_prefix}' and global identifiers.")
                try:
                    start_ref = construct_tag(repo_info.tag_prefix, next_newest_version_identifier)
                    end_ref = construct_tag(repo_info.tag_prefix, newest_version_identifier)
                except ValueError as e:
                    self.logger.error(f"Error constructing tags for {repo_info.repo_name}: {e}. Skipping analysis for this repo.")
                    continue

                self.logger.info(f"Analyzing commits for {repo_info.repo_name} between constructed tags: {start_ref} -> {end_ref}")

                commit_details: List[Dict[str, str]] = self.git_operator.get_commits_between(
                    repository_path=repo_info.repo_path,
                    start_ref=start_ref,
                    end_ref=end_ref
                )

                repo_info.commit_details = commit_details
                self.logger.info(f"Found {len(commit_details)} commits for {repo_info.repo_name} between {start_ref} and {end_ref}.")

            except Exception as e:
                self.logger.error(f"Error during commit analysis for repository {repo_info.repo_name}: {e}")
                self.logger.debug(traceback.format_exc())

        self.logger.info("Finished commit analysis for all repositories.")