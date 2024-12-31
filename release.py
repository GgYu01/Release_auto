from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.rich_logger import RichLogger

logger = RichLogger("release")

def main():
    try:
        repo_manager = RepoManager(all_repos_config)
        repo_manager.initialize_git_repos()

        for git_repo in all_repos_config.all_git_repos():
            logger.info(f"[bold blue]Git Repo Name[/]: {git_repo.repo_name}")
            logger.info(f"[bold blue]Git Repo Path[/]: {git_repo.path}")
            logger.info(f"[bold blue]Git Repo Type[/]: {git_repo.repo_type}")
            logger.info(f"[bold blue]Parent Repo[/]: {git_repo.parent_repo}")
            logger.info("-" * 20)
        
        logger.save_html()

    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

if __name__ == "__main__":
    main()
