from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.custom_logger import Logger, set_request_id
from utils.command_executor import CommandExecutor
from core.builder import BuildSystem
from config.schemas import BuildConfig
from core.git_tag_manager import GitTagFetcher

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
        
        build_system = BuildSystem(build_config, command_executor)
        build_success = build_system.build()
        
        if build_success:
            git_tag_fetcher = GitTagFetcher(command_executor, logger)
            git_tag_fetcher.update_repo_tags(all_repos_config)
            logger.info("Build process completed successfully")
            return 0
        else:
            logger.error("Build process failed")
            return 1

    except Exception as e:
        logger.error(f"An error occurred in main: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
