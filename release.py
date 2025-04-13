import sys
from typing import List, Tuple, Optional, Dict # Added Dict
from config.schemas import CommitDetail, AllReposConfig, GitRepoInfo
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
import os # Needed for path operations
from core.patch_generator import PatchGenerator
from core.packager import ReleasePackager
from core.deployer import Deployer
# TODO: Ensure FileOperator exists and is imported if needed by ReleasePackager
# from utils.file_utils import FileOperator

logger = Logger("release")
set_request_id("release_process")

# --- Start: New Repository Helper Functions ---

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

# --- End: New Repository Helper Functions ---

# Note: _find_repo_info is kept for potential compatibility or specific single-repo needs elsewhere,
# but the new functions are preferred for the Nebula logic.
def _find_repo_info(all_repos_config: AllReposConfig, repo_name: str, repo_parent: Optional[str] = None) -> Optional[GitRepoInfo]:
    """Helper to find a specific GitRepoInfo."""
    for repo in all_repos_config.all_git_repos():
        if repo.repo_name == repo_name:
            if repo_parent is None or repo.repo_parent == repo_parent:
                logger.debug(f"Found repo by name='{repo_name}', parent='{repo_parent}' using legacy _find_repo_info")
                return repo

    # Fallback check using path for specific ALPS GRT case if primary fails
    alps_grt_path_suffix = 'alps/vendor/mediatek/proprietary/trustzone/grt'
    # Adjust parent check to be more flexible if needed, or rely on path suffix primarily
    if repo_name == 'grt': # repo_parent check removed for broader path suffix search
         repo_found_by_path = _find_repo_by_path_suffix(all_repos_config, alps_grt_path_suffix)
         if repo_found_by_path:
              logger.debug(f"Found ALPS GRT repo by path suffix using legacy _find_repo_info fallback: {repo_found_by_path.repo_path}")
              return repo_found_by_path

    logger.warning(f"Could not find repo info for name='{repo_name}', parent='{repo_parent}' using legacy _find_repo_info")
    return None


def _process_nebula_mappings(all_repos_config: AllReposConfig, logger: Logger) -> Dict[str, List[str]]:
    """
    Identifies special commits in source GRT repos, removes them, and maps them
    to commits in Nebula child repositories.

    Args:
        all_repos_config: The configuration containing all repo info.
        logger: The logger instance.

    Returns:
        A dictionary mapping Nebula child commit IDs to a list of associated
        special commit IDs found in the source GRT repositories.
    """
    logger.info("Starting Nebula special commit mapping and extraction process...")

    # --- 1. Identify Target and Source Repos ---
    nebula_child_repos = _find_repos_by_parent(all_repos_config, 'nebula')
    if not nebula_child_repos:
        logger.warning("No child repositories found with parent 'nebula'. Skipping Nebula mapping.")
        return {}
    logger.info(f"Found {len(nebula_child_repos)} Nebula child repositories to process.")

    grt_repos = _find_repos_by_name(all_repos_config, 'grt')
    alps_grt_path_suffix = 'alps/vendor/mediatek/proprietary/trustzone/grt'
    alps_grt_repo = _find_repo_by_path_suffix(all_repos_config, alps_grt_path_suffix)

    source_repos_to_scan: List[GitRepoInfo] = grt_repos
    if alps_grt_repo and alps_grt_repo not in source_repos_to_scan:
        logger.info(f"Adding specific ALPS GRT repo by path suffix ({alps_grt_path_suffix}) to scan list.")
        source_repos_to_scan.append(alps_grt_repo)

    if not source_repos_to_scan:
        logger.warning("No GRT source repositories (by name 'grt' or specific ALPS path) found. Cannot perform Nebula mapping.")
        return {}
    logger.info(f"Identified {len(source_repos_to_scan)} source repositories to scan for special commits.")

    # --- 2. Scan Source Repos for Special Commits ---
    special_patterns = {
        "nebula-hyper": "] thyp-sdk: ",
        "nebula-sdk": "] nebula-sdk: ",
        "TEE": "] tee: ",
    }
    special_commits_storage: List[Tuple[str, CommitDetail]] = [] # (module_name, commit_detail)

    logger.debug(f"Scanning source repos for special commits: {[r.repo_name + (' (' + r.repo_parent + ')' if r.repo_parent else '') for r in source_repos_to_scan]}")
    for source_repo in source_repos_to_scan:
        commits_to_remove: List[CommitDetail] = []
        if not source_repo.commit_details:
            logger.debug(f"No commits to analyze in source repo {source_repo.repo_name} (Path: {source_repo.repo_path})")
            continue

        for commit in source_repo.commit_details:
            found_pattern = False
            for module_name, pattern in special_patterns.items():
                if pattern in commit.message:
                    logger.info(f"Found special commit in {source_repo.repo_name} (Path: {source_repo.repo_path}): {commit.id[:7]} ({module_name})")
                    special_commits_storage.append((module_name, commit))
                    commits_to_remove.append(commit)
                    found_pattern = True
                    break # Assign to first matching pattern
            if found_pattern:
                continue

        # --- 3. Remove Special Commits from Source Repos ---
        if commits_to_remove:
            original_count = len(source_repo.commit_details)
            ids_to_remove = {c.id for c in commits_to_remove} # Use set for efficient lookup
            source_repo.commit_details = [
                c for c in source_repo.commit_details if c.id not in ids_to_remove
            ]
            removed_count = original_count - len(source_repo.commit_details)
            logger.info(f"Removed {removed_count} special commits from source repo {source_repo.repo_name} (Path: {source_repo.repo_path})")
        else:
            logger.debug(f"No special commits found to remove from {source_repo.repo_name} (Path: {source_repo.repo_path})")

    if not special_commits_storage:
        logger.info("No special commits found in any source repository. Skipping Nebula mapping.")
        return {}

    # --- 4. Map Special Commits to Nebula Child Commits ---
    logger.info(f"Mapping {len(special_commits_storage)} special commits' modules and IDs to Nebula child commits.")
    special_commit_ids = [commit.id for module, commit in special_commits_storage]
    special_commit_modules = {commit.id: module for module, commit in special_commits_storage} # Map ID to module

    nebula_child_to_special_map: Dict[str, List[str]] = {} # nebula_child_commit.id -> [special_commit_id, ...]

    for nebula_child_repo in nebula_child_repos:
        if not nebula_child_repo.commit_details:
            logger.debug(f"Nebula child repo {nebula_child_repo.repo_name} has no commits. Skipping.")
            continue

        for nebula_commit in nebula_child_repo.commit_details:
            # Populate the map: Nebula commit ID -> List of ALL found special commit IDs
            nebula_child_to_special_map[nebula_commit.id] = special_commit_ids
            logger.debug(f"Mapped Nebula child commit {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}) to {len(special_commit_ids)} special commit IDs.")

            # Update the commit_module field based on *all* mapped special commits
            if nebula_commit.commit_module is None:
                nebula_commit.commit_module = []
            
            # Add module names from the special commits linked to this nebula commit
            # In this logic, all nebula commits are linked to all special commits, so add all module names
            modules_to_add = list(special_commit_modules.values()) # Get all module names found
            nebula_commit.commit_module.extend(m for m in modules_to_add if m not in nebula_commit.commit_module) # Add unique
            
            logger.debug(f"Updated modules for Nebula child commit {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}): {nebula_commit.commit_module}")

    logger.info(f"Finished Nebula mapping. Created map for {len(nebula_child_to_special_map)} Nebula child commits.")
    return nebula_child_to_special_map


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
        # --- Nebula Special Mapping --- 
        nebula_special_commit_map = _process_nebula_mappings(all_repos_config, logger)
        # --- End: New Centralized Version Logic ---


        # --- Instantiate New Components ---
        patch_generator = PatchGenerator(git_operator, logger)
        # Assuming ReleasePackager constructor only needs logger for now
        # If FileOperator needed:
        # from utils.file_utils import FileOperator
        # file_operator = FileOperator(logger)
        # release_packager = ReleasePackager(file_operator, logger)
        release_packager = ReleasePackager(logger=logger) # Adjust if FileOperator needed
        deployer = Deployer(command_executor, logger)

        # Prepare version info dict
        version_info = {
            "newest_id": newest_id,
            "next_newest_id": next_newest_id,
            "latest_tag": newest_tag # Packager needs the full tag for filename template
        }

        package_success = False
        output_zip_path = None
        # Ensure patch_config is available (it's added to AllReposConfig)
        patch_config = all_repos_config.patch_config
        special_commit_patch_map = {} # Define before try block

        try:
            # --- Patch Generation ---
            logger.info("--- Starting Patch Generation Step ---")
            # --- Identify Special Source Repos (again, for passing to patch_generator) ---
            # This seems redundant but required if patch_generator needs the list explicitly
            grt_repos_for_patch = _find_repos_by_name(all_repos_config, 'grt')
            alps_grt_path_suffix_for_patch = 'alps/vendor/mediatek/proprietary/trustzone/grt'
            alps_grt_repo_for_patch = _find_repo_by_path_suffix(all_repos_config, alps_grt_path_suffix_for_patch)
            special_source_repo_infos: List[GitRepoInfo] = grt_repos_for_patch
            if alps_grt_repo_for_patch and alps_grt_repo_for_patch not in special_source_repo_infos:
                special_source_repo_infos.append(alps_grt_repo_for_patch)
            logger.info(f"Passing {len(special_source_repo_infos)} special source repo infos to patch generator.")

            # --- Patch Generation ---
            logger.info("--- Starting Patch Generation Step ---")
            special_commit_patch_map = patch_generator.generate_patches(
                all_repos_config=all_repos_config,
                version_info=version_info,
                patch_config=patch_config,
                special_source_repo_infos=special_source_repo_infos # Pass the identified source repos
            )

            # --- Link Nebula Patches ---
            logger.info("--- Starting Nebula Patch Linking Step ---")
            # Pass the map generated by _process_nebula_mappings
            patch_generator.link_nebula_patches(
                all_repos_config=all_repos_config,
                special_commit_patch_map=special_commit_patch_map,
                nebula_child_to_special_mapping=nebula_special_commit_map # Use the map from processing step
            )

            # --- Packaging ---
            logger.info("--- Starting Packaging Step ---")
            # Get package config from AllReposConfig
            package_config = all_repos_config.package_config
            # Determine final zip filename
            zip_filename = package_config.zip_name_template.format(
                project_name=package_config.project_name,
                latest_tag=version_info['latest_tag']
            )
            # Assume output zip goes into the current working directory
            output_dir = "."
            output_zip_path = os.path.abspath(os.path.join(output_dir, zip_filename))

            package_success = release_packager.package_release(
                all_repos_config=all_repos_config,
                version_info=version_info,
                temp_patch_dir=patch_config.temp_patch_dir,
                package_config=package_config,
                output_zip_path=output_zip_path
            )

            # --- Deployment ---
            if package_success:
                logger.info("--- Starting Deployment Step ---")
                # Get deploy config from AllReposConfig
                deploy_config = all_repos_config.deploy_config
                if deploy_config:
                    # Example using execute_shell_command if deploy_package is just SCP
                    # deploy_success = deployer.execute_shell_command(f"scp {output_zip_path} {deploy_config.target_server}:{deploy_config.target_path}")
                    # Use the actual method available in Deployer
                    deploy_success = deployer.deploy_package( # Assuming deploy_package exists and handles logic
                        local_zip_path=output_zip_path,
                        deploy_config=deploy_config
                    )
                    if deploy_success:
                        logger.info("Deployment completed successfully.")
                    else:
                        logger.error("Deployment failed.")
                        # Optional: return 1 here if deployment failure is critical
                else:
                    logger.warning("No deployment configuration found in AllReposConfig. Skipping deployment.")
            else:
                logger.error("Packaging failed. Skipping deployment.")

        finally:
            # --- Cleanup ---
            logger.info("--- Starting Cleanup Step ---")
            patch_generator.cleanup_temp_patches(patch_config)


        # --- Final Logging (Adjusted) ---
        logger.info("--- Final Repository Commit Details ---")

        # Existing verbose logging (kept as per original structure)
        for git_repo in all_repos_config.all_git_repos():
            logger.info(f"Git Repo Name: {git_repo.repo_name}")
            logger.info(f"Git Repo Path: {git_repo.path}")
            logger.info(f"Analyze Commit: {git_repo.analyze_commit}")
            if git_repo.analyze_commit:
                logger.info(f"Commit Details Count: {len(git_repo.commit_details)}")
            logger.info("-" * 40)
            if git_repo.analyze_commit and git_repo.commit_details:
                logger.info(f"--- Commit Details for {git_repo.repo_name} ---")
                for commit_detail in git_repo.commit_details: # Use CommitDetail object
                    logger.info(f"  Author: {commit_detail.author}")
                    logger.info(f"  Commit: {commit_detail.id}")
                    if commit_detail.commit_module: # Log module if present
                        logger.info(f"  Modules: {commit_detail.commit_module}")
                    # Log patch path (could be str, List[str], or None)
                    patch_path_log = str(commit_detail.patch_path) if commit_detail.patch_path is not None else 'None'
                    logger.info(f"  Patch Path: {patch_path_log}")
                    message_lines = commit_detail.message.splitlines()
                    logger.info(f"  Message: {message_lines[0] if message_lines else ''}")
                    for line in message_lines[1:]:
                         logger.info(f"           {line}")
                    logger.info(f"  {'-'*20}")

        logger.info("Release process finished.")
        return 0

    except Exception as e:
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
