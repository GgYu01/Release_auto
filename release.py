from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.custom_logger import Logger, set_request_id
from utils.command_executor import CommandExecutor
from core.builder import BuildSystem
from config.schemas import BuildConfig
from core.git_tag_manager import GitTagFetcher
from core.sync.repo_synchronizer import RepoSynchronizer
from config.sync_config import sync_strategies_config
from config.tagging_config import TaggingConfig
from core.tagger import Tagger
from core.merger import GerritMerger
from utils.git_utils import GitOperator
from core.commit_analyzer import CommitAnalyzer

logger = Logger("release")

# Bootstrap logging context
set_request_id("release_process")

def main():
    logger.info("Starting release process...")
    try:
        build_config = BuildConfig()
        command_executor = CommandExecutor()
        
        repo_manager = RepoManager(all_repos_config)
        repo_manager.initialize_git_repos()
        

        # --- Initialize Core Components ---
        git_operator = GitOperator(command_executor)
        git_tag_fetcher = GitTagFetcher(command_executor, logger)
        commit_analyzer = CommitAnalyzer(git_operator, logger)

        # --- Fetch Tags --- 
        # This step populates newest_version and next_newest_version in repo_info
        git_tag_fetcher.update_repo_tags(all_repos_config)

        # --- Analyze Commits ---
        # This step uses the fetched tags to find commits and populates commit_details
        commit_analyzer.analyze_all_repositories(all_repos_config)

        # # Placeholder for where commit analysis/patching might populate commit data
        # # For now, create an empty map. This needs to be replaced with actual data later.
        # commits_to_merge_map: Dict[str, List[str]] = {}
        # logger.warning("Using placeholder empty commits_map for GerritMerger. This needs real data.")

        # # Instantiate GitOperator and GerritMerger
        # git_operator = GitOperator(command_executor)
        # gerrit_merger = GerritMerger(command_executor, git_operator, logger)

        # # Get the list of GitRepoInfo objects
        # repos_to_process = list(all_repos_config.all_git_repos())

        # # Perform Gerrit Merges
        # merge_success = gerrit_merger.process_merges(repos_to_process, commits_to_merge_map)

        # if not merge_success:
        #     logger.error("Gerrit merge process encountered errors. Check logs.")
        #     # Decide if failure should halt the process, e.g., return 1
        #     # return 1 # Optional: uncomment to halt on merge failure

        # --- Resume other steps ---

        # repo_synchronizer = RepoSynchronizer(all_repos_config, sync_strategies_config, command_executor)
        # repo_synchronizer.sync_repos()

        # tagging_config = TaggingConfig()
        # tagger = Tagger(tagging_config, command_executor)
        # tagger.tag_repositories()
        # build_system = BuildSystem(build_config, command_executor)
        # build_success = build_system.build()
        
        # if build_success:
        #     # git_tag_fetcher = GitTagFetcher(command_executor, logger)
        #     # git_tag_fetcher.update_repo_tags(all_repos_config)
        #     logger.info("Build process completed successfully")
        #     return 0
        # else:
        #     logger.error("Build process failed")
        #     return 1

        for git_repo in all_repos_config.all_git_repos():
            logger.info(f"Git Repo Name: {git_repo.repo_name}")
            logger.info(f"Git Repo Path: {git_repo.path}")
            logger.info(f"Git Repo Type: {git_repo.repo_type}")
            logger.info(f"Parent Repo: {git_repo.parent_repo}")
            logger.info(f"Tag Prefix: {git_repo.tag_prefix}")
            logger.info(f"Remote Name: {git_repo.remote_name}")
            logger.info(f"Remote Branch: {git_repo.remote_branch}")
            logger.info(f"Local Branch: {git_repo.local_branch}")
            logger.info(f"Newest Version: {git_repo.newest_version}")
            logger.info(f"Next Newest Version: {git_repo.next_newest_version}")
            logger.info(f"Analyze Commit: {git_repo.analyze_commit}")
            logger.info(f"Generate Patch: {git_repo.generate_patch}")
            logger.info(f"Branch Info: {git_repo.branch_info}")
            logger.info(f"Push Template: {git_repo.push_template}")
            logger.info("-" * 40)


    except Exception as e:
        logger.error(f"An error occurred in main: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
