import sys
from typing import Optional
from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.custom_logger import Logger, set_request_id
from utils.command_executor import CommandExecutor
from core.builder import BuildSystem
from config.schemas import BuildConfig, RepoConfig, GitRepoInfo
from core.git_tag_manager import GitTagFetcher
from core.sync.repo_synchronizer import RepoSynchronizer
from config.sync_config import sync_strategies_config
from config.tagging_config import TaggingConfig
from core.tagger import Tagger
from core.merger import GerritMerger
from utils.git_utils import GitOperator
from core.commit_analyzer import CommitAnalyzer
from utils.tag_utils import extract_version_identifier

logger = Logger("release")
set_request_id("release_process")

def main() -> int:
    logger.info("Starting release process...")
    try:
        build_config = BuildConfig()
        command_executor = CommandExecutor()
        git_operator = GitOperator(command_executor)

        repo_manager = RepoManager(all_repos_config)
        repo_manager.initialize_git_repos()

        # --- Start: New Centralized Version Logic ---
        source_repo_name = all_repos_config.version_source_repo_name
        if not source_repo_name:
            logger.critical("Config Error: 'version_source_repo_name' missing.")
            return 1

        source_repo_config: Optional[RepoConfig] = all_repos_config.repo_configs.get(source_repo_name)
        if not source_repo_config:
            logger.critical(f"Config Error: Source repo '{source_repo_name}' not found.")
            return 1

        source_repo_info: Optional[GitRepoInfo] = None
        for info in source_repo_config.git_repos:
            if info.repo_type == "git":
                source_repo_info = info
                break

        if not source_repo_info:
            logger.critical(f"Config Error: No GitRepoInfo for '{source_repo_name}'.")
            return 1

        if not source_repo_info.repo_path or not source_repo_info.local_branch:
            logger.critical(f"Config Error: Path or branch missing for '{source_repo_name}'.")
            return 1

        git_tag_fetcher = GitTagFetcher(command_executor, logger)
        logger.info(f"Fetching tags from source: '{source_repo_name}'")
        newest_tag, next_newest_tag = git_tag_fetcher.fetch_latest_tags(
            repo_path=source_repo_info.repo_path,
            branch_name=source_repo_info.local_branch,
            remote_name=source_repo_info.remote_name or "origin",
            tag_prefix=source_repo_info.tag_prefix
        )

        if newest_tag is None or next_newest_tag is None:
            logger.critical(f"Tag fetch failed for '{source_repo_name}'.")
            return 1
        logger.info(f"Source tags: Newest='{newest_tag}', Next='{next_newest_tag}'")

        logger.info("Extracting global identifiers...")
        newest_id = extract_version_identifier(newest_tag, source_repo_info.tag_prefix)
        next_newest_id = extract_version_identifier(next_newest_tag, source_repo_info.tag_prefix)

        if newest_id is None or next_newest_id is None:
            logger.critical(f"Identifier extraction failed from source tags.")
            return 1
        logger.info(f"Global IDs: Newest='{newest_id}', Next='{next_newest_id}'")

        commit_analyzer = CommitAnalyzer(git_operator, logger)
        commit_analyzer.analyze_all_repositories(
            all_repos_config, newest_id, next_newest_id
        )
        # --- End: New Centralized Version Logic ---

        # --- Original steps (potentially using results from above) ---
        # git_tag_fetcher.update_repo_tags(all_repos_config) # Old logic disabled
        # commit_analyzer.analyze_all_repositories(all_repos_config) # Old logic disabled

        # Placeholder for other existing steps if needed
        # logger.warning("Skipping other original steps like merge, sync, tag, build for now.")

        # Existing verbose logging (kept as per original structure)
        for git_repo in all_repos_config.all_git_repos():
            logger.info(f"Git Repo Name: {git_repo.repo_name}")
            logger.info(f"Git Repo Path: {git_repo.path}")
            logger.info(f"Analyze Commit: {git_repo.analyze_commit}")
            if git_repo.analyze_commit:
                logger.info(f"Commit Details Count: {len(git_repo.commit_details)}")
            logger.info("-" * 40)

        logger.info("Release process finished.")
        return 0

    except Exception as e:
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
