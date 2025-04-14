import sys
import os
import shutil # Needed for cleanup, though handled by PatchGenerator
from typing import List, Tuple, Optional, Dict
from config.schemas import (
    CommitDetail, AllReposConfig, GitRepoInfo, RepoConfig, PatchConfig,
    PackageConfig, DeployConfig
)
from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.custom_logger import Logger, set_request_id
from utils.command_executor import CommandExecutor
# BuildSystem import removed as building is not part of this workflow
# from core.builder import BuildSystem
# from config.schemas import BuildConfig
from core.git_tag_manager import GitTagFetcher
# Sync imports removed as syncing is not part of this workflow
# from core.sync.repo_synchronizer import RepoSynchronizer
# from config.sync_config import sync_strategies_config
# from config.tagging_config import TaggingConfig
# from core.tagger import Tagger
# from core.merger import GerritMerger
from utils.git_utils import GitOperator
from core.commit_analyzer import CommitAnalyzer
from utils.tag_utils import extract_version_identifier, construct_tag # Added construct_tag
from core.patch_generator import PatchGenerator, SPECIAL_PATTERNS # Import patterns
from core.packager import ReleasePackager
from core.deployer import Deployer

logger = Logger("release")
set_request_id("release_process") # Example request ID

# --- Repository Helper Functions (Keep as they are useful) ---

def _find_repos_by_name(all_repos_config: AllReposConfig, repo_name: str) -> List[GitRepoInfo]:
    """Finds all GitRepoInfo objects with a specific repo_name."""
    found_repos = [
        repo for repo in all_repos_config.all_git_repos()
        if repo.repo_name == repo_name
    ]
    logger.debug(f"Found {len(found_repos)} repos with name='{repo_name}'.")
    return found_repos

def _find_repo_by_path_suffix(all_repos_config: AllReposConfig, path_suffix: str) -> Optional[GitRepoInfo]:
    """Finds the first GitRepoInfo whose repo_path ends with the given suffix."""
    normalized_suffix = path_suffix.replace('\\', '/')
    for repo in all_repos_config.all_git_repos():
        if repo.repo_path and repo.repo_path.replace('\\', '/').endswith(normalized_suffix):
            logger.debug(f"Found repo by path suffix '{path_suffix}': {repo.repo_path}")
            return repo
    logger.debug(f"No repo found with path suffix '{path_suffix}'.")
    return None

def _find_repos_by_parent(all_repos_config: AllReposConfig, parent_name: str) -> List[GitRepoInfo]:
    """Finds all GitRepoInfo objects with a specific repo_parent."""
    found_repos = [
        repo for repo in all_repos_config.all_git_repos()
        if repo.repo_parent == parent_name
    ]
    logger.debug(f"Found {len(found_repos)} repos with parent='{parent_name}'.")
    return found_repos

# --- Refactored Nebula Mapping Function ---

def _process_nebula_mappings(
    all_repos_config: AllReposConfig,
    special_source_repo_infos: List[GitRepoInfo],
    logger: Logger
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Identifies special commits in source GRT repos, builds mappings, and removes
    the special commits from the source repos' commit lists within all_repos_config.

    Args:
        all_repos_config: The configuration containing all repo info (will be modified in-place).
        special_source_repo_infos: List of GitRepoInfo objects for repos considered sources of special commits.
        logger: The logger instance.

    Returns:
        A tuple containing:
        - nebula_child_to_special_map: Dict mapping Nebula child commit IDs to a list of associated special commit IDs.
        - special_commit_messages: Dict mapping special commit IDs to their full messages.
    """
    logger.info("Starting Nebula special commit identification, mapping, and extraction process...")

    nebula_child_repos = _find_repos_by_parent(all_repos_config, 'nebula')
    if not nebula_child_repos:
        logger.warning("No child repositories found with parent 'nebula'. Skipping Nebula processing.")
        return {}, {} # Return empty maps

    if not special_source_repo_infos:
        logger.warning("No special source repositories identified. Cannot perform Nebula mapping.")
        return {}, {}

    logger.info(f"Identified {len(special_source_repo_infos)} source repositories to scan for special commits.")
    logger.info(f"Found {len(nebula_child_repos)} Nebula child repositories.")

    # --- 1. Scan Source Repos for Special Commits ---
    special_commits_found: List[CommitDetail] = []
    source_repo_paths_with_special_commits: Dict[str, List[CommitDetail]] = {} # repo_path -> list of special commits in that repo

    for source_repo in special_source_repo_infos:
        repo_log_name = f"{source_repo.repo_parent}/{source_repo.repo_name}" if source_repo.repo_parent else source_repo.repo_name
        if not source_repo.commit_details:
            logger.debug(f"No commits to analyze in source repo {repo_log_name} (Path: {source_repo.repo_path})")
            continue

        found_in_repo = []
        for commit in source_repo.commit_details:
            # Check if commit message contains any special pattern
            if any(pattern in commit.message for pattern in SPECIAL_PATTERNS.values()):
                 logger.info(f"Found special commit in {repo_log_name} (Path: {source_repo.repo_path}): {commit.id[:7]}")
                 special_commits_found.append(commit)
                 found_in_repo.append(commit)

        if found_in_repo and source_repo.repo_path:
             source_repo_paths_with_special_commits[source_repo.repo_path] = found_in_repo

    if not special_commits_found:
        logger.info("No special commits found in any designated source repository. Skipping Nebula mapping.")
        return {}, {}

    # --- 2. Build Mappings ---
    special_commit_ids = [commit.id for commit in special_commits_found]
    special_commit_messages: Dict[str, str] = {commit.id: commit.message for commit in special_commits_found}
    nebula_child_to_special_map: Dict[str, List[str]] = {} # nebula_child_commit.id -> [special_commit_id, ...]

    logger.info(f"Building map for {len(nebula_child_repos)} Nebula child repos to {len(special_commit_ids)} special commits.")
    for nebula_child_repo in nebula_child_repos:
        if not nebula_child_repo.commit_details:
            continue
        for nebula_commit in nebula_child_repo.commit_details:
            # Map Nebula child commit ID -> List of ALL found special commit IDs (as per requirement)
            nebula_child_to_special_map[nebula_commit.id] = special_commit_ids
            logger.debug(f"Mapped Nebula child {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}) -> {len(special_commit_ids)} special IDs.")

    # --- 3. Remove Special Commits from Source Repos (Modify all_repos_config in-place) ---
    logger.info("Removing identified special commits from their source repositories...")
    special_commit_id_set = set(special_commit_ids) # Use set for efficient lookup

    for source_repo in special_source_repo_infos:
         if not source_repo.commit_details:
             continue # Skip if no commits to begin with

         original_count = len(source_repo.commit_details)
         # Filter out commits whose IDs are in the special set
         source_repo.commit_details = [
             c for c in source_repo.commit_details if c.id not in special_commit_id_set
         ]
         removed_count = original_count - len(source_repo.commit_details)
         if removed_count > 0:
             repo_log_name = f"{source_repo.repo_parent}/{source_repo.repo_name}" if source_repo.repo_parent else source_repo.repo_name
             logger.info(f"Removed {removed_count} special commits from source repo {repo_log_name} (Path: {source_repo.repo_path})")

    logger.info(f"Finished Nebula processing. Mapped {len(nebula_child_to_special_map)} child commits. Stored {len(special_commit_messages)} special messages.")
    return nebula_child_to_special_map, special_commit_messages


# --- Main Execution Function ---

def main() -> int:
    logger.info("========================================")
    logger.info("Starting GR Release Automation Workflow")
    logger.info("========================================")
    output_zip_path = None # Initialize for finally block
    patch_generator = None # Initialize for finally block
    patch_config = None # Initialize for finally block

    try:
        # --- 1. Initialization ---
        logger.info("--- Step 1: Initialization ---")
        command_executor = CommandExecutor()
        git_operator = GitOperator(command_executor)
        repo_manager = RepoManager(all_repos_config) # Initializes GitRepoInfo objects
        repo_manager.initialize_git_repos() # Parses manifests, calculates paths
        git_tag_fetcher = GitTagFetcher(command_executor, logger)
        commit_analyzer = CommitAnalyzer(git_operator, logger)
        patch_generator = PatchGenerator(git_operator, logger)
        release_packager = ReleasePackager(logger=logger)
        deployer = Deployer(command_executor, logger)

        # Get necessary config sections
        patch_config = all_repos_config.patch_config
        package_config = all_repos_config.package_config
        deploy_config = all_repos_config.deploy_config # Optional

        # --- 2. Fetch Central Version Tags ---
        logger.info("--- Step 2: Fetching Central Version Tags ---")
        source_repo_name = all_repos_config.version_source_repo_name
        if not source_repo_name:
            logger.critical("Config Error: 'version_source_repo_name' missing.")
            return 1
        # Find the source GitRepoInfo for tag fetching (assuming it's directly configured or first under the name)
        source_repo_infos = [r for r in all_repos_config.all_git_repos() if r.repo_name == source_repo_name and r.repo_type == 'git']
        if not source_repo_infos:
             logger.critical(f"Config Error: No source GitRepoInfo found for '{source_repo_name}'.")
             return 1
        source_repo_info = source_repo_infos[0] # Use the first found matching git repo
        if not source_repo_info.repo_path or not source_repo_info.local_branch:
             logger.critical(f"Config Error: Path or branch missing for source repo '{source_repo_name}'.")
             return 1

        newest_tag, next_newest_tag = git_tag_fetcher.fetch_latest_tags(
            repo_path=source_repo_info.repo_path,
            branch_name=source_repo_info.local_branch,
            remote_name=source_repo_info.remote_name or "origin",
            tag_prefix=source_repo_info.tag_prefix
        )
        if newest_tag is None or next_newest_tag is None:
            logger.critical(f"Tag fetch failed for source repo '{source_repo_name}'. Cannot proceed.")
            return 1
        logger.info(f"Source tags fetched: Newest='{newest_tag}', Next='{next_newest_tag}'")

        newest_id = extract_version_identifier(newest_tag, source_repo_info.tag_prefix)
        next_newest_id = extract_version_identifier(next_newest_tag, source_repo_info.tag_prefix)
        if newest_id is None or next_newest_id is None:
            logger.critical("Identifier extraction failed from source tags. Cannot proceed.")
            return 1
        logger.info(f"Global Version IDs: Newest='{newest_id}', Next='{next_newest_id}'")

        version_info = {
            "newest_id": newest_id,
            "next_newest_id": next_newest_id,
            "latest_tag": newest_tag # Needed for packaging template
        }

        # --- 3. Analyze Commits ---
        logger.info("--- Step 3: Analyzing Commits ---")
        # This populates commit_details in all_repos_config for repos with analyze_commit=True
        commit_analyzer.analyze_all_repositories(
            all_repos_config, newest_id, next_newest_id
        )
        logger.info("Commit analysis completed.")
        # Note: At this point, all_repos_config contains the *full* commit lists

        # --- 4. Identify Special Source Repos ---
        logger.info("--- Step 4: Identifying Special Source Repositories ---")
        # Find 'grt' repos by name and the specific ALPS GRT repo by path suffix
        grt_repos_sources = _find_repos_by_name(all_repos_config, 'grt')
        alps_grt_path_suffix = 'alps/vendor/mediatek/proprietary/trustzone/grt'
        alps_grt_repo_source = _find_repo_by_path_suffix(all_repos_config, alps_grt_path_suffix)

        special_source_repo_infos: List[GitRepoInfo] = grt_repos_sources
        if alps_grt_repo_source and alps_grt_repo_source not in special_source_repo_infos:
             logger.info(f"Adding specific ALPS GRT repo ({alps_grt_path_suffix}) to special sources.")
             special_source_repo_infos.append(alps_grt_repo_source)
        logger.info(f"Identified {len(special_source_repo_infos)} potential special source repos.")

        # --- 5. Generate Patches ---
        logger.info("--- Step 5: Generating Patches ---")
        # Pass the UNMODIFIED all_repos_config (with full commit lists)
        special_commit_patch_map = patch_generator.generate_patches(
            all_repos_config=all_repos_config,
            version_info=version_info,
            patch_config=patch_config,
            special_source_repo_infos=special_source_repo_infos # Pass identified sources
        )
        logger.info(f"Patch generation finished. Found {len(special_commit_patch_map)} special patches.")
        # Note: generate_patches populates commit_detail.patch_path for eligible commits

        # --- 6. Process Nebula Mappings (Identify, Map, THEN Remove) ---
        logger.info("--- Step 6: Processing Nebula Mappings ---")
        # This function modifies all_repos_config IN-PLACE by removing special commits from sources
        nebula_child_to_special_map, special_commit_messages = _process_nebula_mappings(
            all_repos_config=all_repos_config, # Pass config to be modified
            special_source_repo_infos=special_source_repo_infos,
            logger=logger
        )
        logger.info("Nebula mapping and special commit removal finished.")
        # Note: all_repos_config now has special commits removed from source repo lists

        # --- 7. Link Nebula Patches ---
        logger.info("--- Step 7: Linking Nebula Patches & Assigning Modules ---")
        # Pass the MODIFIED all_repos_config, maps, and messages
        patch_generator.link_nebula_patches(
            all_repos_config=all_repos_config, # Modified config
            special_commit_patch_map=special_commit_patch_map,
            nebula_child_to_special_mapping=nebula_child_to_special_map,
            special_commit_messages=special_commit_messages # Pass the messages map
        )
        logger.info("Nebula patch linking finished.")
        # Note: commit_detail.patch_path and commit_detail.commit_module updated for Nebula children

        # --- 8. Package Release ---
        logger.info("--- Step 8: Packaging Release ---")
        package_success = False
        zip_filename = package_config.zip_name_template.format(
            project_name=package_config.project_name,
            latest_tag=version_info['latest_tag'] # Use the full tag
        )
        # Place ZIP in the current working directory (or configure via PackageConfig if needed)
        output_dir = "."
        output_zip_path = os.path.abspath(os.path.join(output_dir, zip_filename))

        package_success = release_packager.package_release(
            all_repos_config=all_repos_config, # Final state of config
            version_info=version_info,
            temp_patch_dir=patch_config.temp_patch_dir,
            package_config=package_config,
            output_zip_path=output_zip_path
        )

        # --- 9. Deploy Package ---
        if package_success:
            logger.info("--- Step 9: Deploying Package ---")
            if deploy_config:
                logger.info(f"Deploying {output_zip_path} to {deploy_config.scp_user}@{deploy_config.scp_host}:{deploy_config.scp_remote_path}")
                deploy_success = deployer.deploy_package(
                    local_zip_path=output_zip_path,
                    deploy_config=deploy_config
                )
                if deploy_success:
                    logger.info("Deployment completed successfully.")
                else:
                    logger.error("Deployment failed.")
                    # Decide if deployment failure should cause non-zero exit
                    # return 1 # Optional: uncomment if deployment failure is critical
            else:
                logger.warning("No deployment configuration found (deploy_config). Skipping deployment.")
        else:
            logger.error("Packaging failed. Skipping deployment.")
            return 1 # Packaging failure is critical

        # --- Final Logging (Optional: Review details) ---
        logger.info("--- Final Commit Details (Post-Processing) ---")
        # Keep or remove this verbose logging as needed
        for git_repo in all_repos_config.all_git_repos():
             repo_log_name = f"{git_repo.repo_parent}/{git_repo.repo_name}" if git_repo.repo_parent else git_repo.repo_name
             logger.debug(f"--- Details for {repo_log_name} ---")
             logger.debug(f"  Path: {git_repo.path}")
             logger.debug(f"  Analyze Commit: {git_repo.analyze_commit}")
             logger.debug(f"  Generate Patch: {git_repo.generate_patch}")
             if git_repo.commit_details:
                 logger.debug(f"  Commit Count: {len(git_repo.commit_details)}")
                 for i, commit_detail in enumerate(git_repo.commit_details):
                     logger.debug(f"    Commit #{i+1}: {commit_detail.id[:7]}")
                     logger.debug(f"      Author: {commit_detail.author}")
                     logger.debug(f"      Modules: {commit_detail.commit_module}")
                     logger.debug(f"      Patch Path: {commit_detail.patch_path}")
                     # Log first line of message
                     msg_first_line = commit_detail.message.splitlines()[0] if commit_detail.message else ""
                     logger.debug(f"      Message: {msg_first_line}...")
             else:
                 logger.debug(f"  Commit Count: 0")
             logger.debug("-" * 20)

        logger.info("=========================================")
        logger.info("GR Release Automation Workflow Finished Successfully.")
        logger.info(f"Output package: {output_zip_path if package_success else 'N/A (Packaging Failed)'}")
        logger.info("=========================================")
        return 0 # Success

    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during the release workflow: {e}", exc_info=True)
        return 1 # Indicate failure

    finally:
        # --- 10. Cleanup ---
        logger.info("--- Step 10: Cleanup ---")
        if patch_generator and patch_config:
            patch_generator.cleanup_temp_patches(patch_config)
        else:
            logger.warning("Cleanup skipped: PatchGenerator or PatchConfig not initialized.")

if __name__ == "__main__":
    sys.exit(main())
