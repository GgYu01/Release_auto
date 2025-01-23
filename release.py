from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.rich_logger import Logger

logger = Logger("release")

def main():
    logger.info("Starting release process...")
    try:
        repo_manager = RepoManager(all_repos_config)
        repo_manager.initialize_git_repos()

        for git_repo in all_repos_config.all_git_repos():
            logger.info(f"Git Repo Name: {git_repo.repo_name}")
            logger.info(f"Git Repo Path: {git_repo.path}")
            logger.info(f"Git Repo Type: {git_repo.repo_type}")
            logger.info(f"Parent Repo: {git_repo.parent_repo}")
            logger.info(f"Tag Prefix: {git_repo.tag_prefix}")
            logger.info(f"Remote Name: {git_repo.remote_name}")
            logger.info(f"Remote Branch: {git_repo.remote_branch}")
            logger.info(f"Commit Analyses: {git_repo.commit_analyses}")
            logger.info(f"Newest Version: {git_repo.newest_version}")
            logger.info(f"Next Newest Version: {git_repo.next_newest_version}")
            logger.info(f"Analyze Commit: {git_repo.analyze_commit}")
            logger.info(f"Generate Patch: {git_repo.generate_patch}")
            logger.info(f"Branch Info: {git_repo.branch_info}")
            logger.info(f"Push Template: {git_repo.push_template}")
            logger.info("-" * 40)
        
        logger.save_html()

    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

if __name__ == "__main__":
    main()
