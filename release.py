import sys
import os
from config.schemas import BuildConfig # Added import
from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.custom_logger import Logger, set_request_id
from utils.command_executor import CommandExecutor
from core.git_tag_manager import GitTagFetcher
from utils.git_utils import GitOperator
from core.commit_analyzer import CommitAnalyzer
from core.patch_generator import PatchGenerator
from core.packager import ReleasePackager
from core.deployer import Deployer
from utils.excel_utils import ExcelReporter
from core.builder import BuildSystem
from core.workflow import ProjectWorkflow # Import the new workflow class
# Import RepoSynchronizer if it exists
try:
    from core.sync.repo_synchronizer import RepoSynchronizer
except ImportError:
    RepoSynchronizer = None

logger = Logger("release")
set_request_id("release_process")


def main() -> int:
    logger.info("Initializing GR Release Automation Tool...")
    patch_generator = None # Initialize for finally block
    patch_config = None

    try:
        # --- Core Component Initialization ---
        command_executor = CommandExecutor()
        git_operator = GitOperator(command_executor)
        repo_manager = RepoManager(all_repos_config) # Assuming init happens here or is separate
        repo_manager.initialize_git_repos() # Explicitly call initialization

        # Initialize other components
        git_tag_fetcher = GitTagFetcher(command_executor, logger)
        commit_analyzer = CommitAnalyzer(git_operator, logger)
        patch_generator = PatchGenerator(git_operator, logger) # Assign for finally block
        patch_config = all_repos_config.patch_config # Assign for finally block
        release_packager = ReleasePackager(logger=logger)
        deployer = Deployer(command_executor, logger)
        excel_reporter = ExcelReporter(logger, git_operator, all_repos_config.excel_config) # Pass config directly

        # Initialize Builder and Synchronizer if available
        build_config_instance = BuildConfig() # Instantiate BuildConfig
        builder = BuildSystem(build_config_instance, command_executor, all_repos_config) # Pass all_repos_config
        # synchronizer = RepoSynchronizer(...) # Initialize if RepoSynchronizer exists and is needed

        # --- Workflow Instantiation ---
        workflow = ProjectWorkflow(
            config=all_repos_config,
            cmd_executor=command_executor,
            git_operator=git_operator,
            repo_manager=repo_manager,
            # synchronizer=synchronizer, # Pass if initialized
            tag_fetcher=git_tag_fetcher,
            builder=builder, # Pass builder instance
            analyzer=commit_analyzer,
            patch_generator=patch_generator,
            excel_reporter=excel_reporter,
            packager=release_packager,
            deployer=deployer,
            logger=logger
        )

        # --- Workflow Execution ---
        logger.info("Handing control to ProjectWorkflow...")
        exit_code = workflow.run_workflow()
        logger.info(f"ProjectWorkflow finished with exit code: {exit_code}")
        return exit_code

    except Exception as e:
        logger.critical(f"A critical error occurred during initialization or workflow execution: {e}", exc_info=True)
        return 1

    finally:
        # --- Cleanup ---
        logger.info("--- Performing Cleanup ---")
        if patch_generator and patch_config:
            patch_generator.cleanup_temp_patches(patch_config)
        else:
            logger.warning("Cleanup skipped: PatchGenerator or PatchConfig not available.")
        logger.info("--- Cleanup Finished ---")


if __name__ == "__main__":
    sys.exit(main())
