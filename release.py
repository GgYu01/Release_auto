import sys
import os
import shutil
from typing import List, Tuple, Optional, Dict
from config.schemas import (
    CommitDetail, AllReposConfig, GitRepoInfo, RepoConfig, PatchConfig,
    PackageConfig, DeployConfig, ExcelConfig
)
from config.repos_config import all_repos_config
from core.repo_manager import RepoManager
from utils.custom_logger import Logger, set_request_id
from utils.command_executor import CommandExecutor
from core.git_tag_manager import GitTagFetcher
from utils.git_utils import GitOperator
from core.commit_analyzer import CommitAnalyzer
from utils.tag_utils import extract_version_identifier, construct_tag
from core.patch_generator import PatchGenerator, SPECIAL_PATTERNS
from core.packager import ReleasePackager
from core.deployer import Deployer
from utils.excel_utils import ExcelReporter

logger = Logger("release")
set_request_id("release_process")

def _find_repos_by_name(all_repos_config: AllReposConfig, repo_name: str) -> List[GitRepoInfo]:
    found_repos = [
        repo for repo in all_repos_config.all_git_repos()
        if repo.repo_name == repo_name
    ]
    logger.debug(f"Found {len(found_repos)} repos with name='{repo_name}'.")
    return found_repos

def _find_repo_by_path_suffix(all_repos_config: AllReposConfig, path_suffix: str) -> Optional[GitRepoInfo]:
    normalized_suffix = path_suffix.replace('\\', '/')
    for repo in all_repos_config.all_git_repos():
        if repo.repo_path and repo.repo_path.replace('\\', '/').endswith(normalized_suffix):
            logger.debug(f"Found repo by path suffix '{path_suffix}': {repo.repo_path}")
            return repo
    logger.debug(f"No repo found with path suffix '{path_suffix}'.")
    return None

def _find_repos_by_parent(all_repos_config: AllReposConfig, parent_name: str) -> List[GitRepoInfo]:
    found_repos = [
        repo for repo in all_repos_config.all_git_repos()
        if repo.repo_parent == parent_name
    ]
    logger.debug(f"Found {len(found_repos)} repos with parent='{parent_name}'.")
    return found_repos

def _process_nebula_mappings(
    all_repos_config: AllReposConfig,
    special_source_repo_infos: List[GitRepoInfo],
    logger: Logger
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    logger.info("Starting Nebula special commit identification, mapping, and extraction process...")

    nebula_child_repos = _find_repos_by_parent(all_repos_config, 'nebula')
    if not nebula_child_repos:
        logger.warning("No child repositories found with parent 'nebula'. Skipping Nebula processing.")
        return {}, {}

    if not special_source_repo_infos:
        logger.warning("No special source repositories identified. Cannot perform Nebula mapping.")
        return {}, {}

    logger.info(f"Identified {len(special_source_repo_infos)} source repositories to scan for special commits.")
    logger.info(f"Found {len(nebula_child_repos)} Nebula child repositories.")

    special_commits_found: List[CommitDetail] = []
    source_repo_paths_with_special_commits: Dict[str, List[CommitDetail]] = {}

    for source_repo in special_source_repo_infos:
        repo_log_name = f"{source_repo.repo_parent}/{source_repo.repo_name}" if source_repo.repo_parent else source_repo.repo_name
        if not source_repo.commit_details:
            logger.debug(f"No commits to analyze in source repo {repo_log_name} (Path: {source_repo.repo_path})")
            continue

        found_in_repo = []
        for commit in source_repo.commit_details:
            if any(pattern in commit.message for pattern in SPECIAL_PATTERNS.values()):
                 logger.info(f"Found special commit in {repo_log_name} (Path: {source_repo.repo_path}): {commit.id[:7]}")
                 special_commits_found.append(commit)
                 found_in_repo.append(commit)

        if found_in_repo and source_repo.repo_path:
             source_repo_paths_with_special_commits[source_repo.repo_path] = found_in_repo

    if not special_commits_found:
        logger.info("No special commits found in any designated source repository. Skipping Nebula mapping.")
        return {}, {}

    special_commit_ids = [commit.id for commit in special_commits_found]
    special_commit_messages: Dict[str, str] = {commit.id: commit.message for commit in special_commits_found}
    nebula_child_to_special_map: Dict[str, List[str]] = {}

    logger.info(f"Building map for {len(nebula_child_repos)} Nebula child repos to {len(special_commit_ids)} special commits.")
    for nebula_child_repo in nebula_child_repos:
        if not nebula_child_repo.commit_details:
            continue
        for nebula_commit in nebula_child_repo.commit_details:
            nebula_child_to_special_map[nebula_commit.id] = special_commit_ids
            logger.debug(f"Mapped Nebula child {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}) -> {len(special_commit_ids)} special IDs.")

    logger.info("Removing identified special commits from their source repositories...")
    special_commit_id_set = set(special_commit_ids)

    for source_repo in special_source_repo_infos:
         if not source_repo.commit_details:
             continue

         original_count = len(source_repo.commit_details)
         source_repo.commit_details = [
             c for c in source_repo.commit_details if c.id not in special_commit_id_set
         ]
         removed_count = original_count - len(source_repo.commit_details)
         if removed_count > 0:
             repo_log_name = f"{source_repo.repo_parent}/{source_repo.repo_name}" if source_repo.repo_parent else source_repo.repo_name
             logger.info(f"Removed {removed_count} special commits from source repo {repo_log_name} (Path: {source_repo.repo_path})")

    logger.info(f"Finished Nebula processing. Mapped {len(nebula_child_to_special_map)} child commits. Stored {len(special_commit_messages)} special messages.")
    return nebula_child_to_special_map, special_commit_messages


def main() -> int:
    logger.info("========================================")
    logger.info("Starting GR Release Automation Workflow")
    logger.info("========================================")
    output_zip_path: Optional[str] = None
    generated_excel_file_path: Optional[str] = None # Renamed for clarity
    patch_generator = None
    patch_config = None

    try:
        logger.info("--- Step 1: Initialization ---")
        command_executor = CommandExecutor()
        git_operator = GitOperator(command_executor)
        repo_manager = RepoManager(all_repos_config)
        repo_manager.initialize_git_repos()
        git_tag_fetcher = GitTagFetcher(command_executor, logger)
        commit_analyzer = CommitAnalyzer(git_operator, logger)
        patch_generator = PatchGenerator(git_operator, logger)
        release_packager = ReleasePackager(logger=logger)
        deployer = Deployer(command_executor, logger)

        patch_config = all_repos_config.patch_config
        package_config = all_repos_config.package_config
        deploy_config = all_repos_config.deploy_config
        excel_config = all_repos_config.excel_config # Get excel config early

        logger.info("--- Step 2: Fetching Central Version Tags ---")
        source_repo_name = all_repos_config.version_source_repo_name
        if not source_repo_name:
            logger.critical("Config Error: 'version_source_repo_name' missing.")
            return 1
        source_repo_infos = [r for r in all_repos_config.all_git_repos() if r.repo_name == source_repo_name and r.repo_type == 'git']
        if not source_repo_infos:
             logger.critical(f"Config Error: No source GitRepoInfo found for '{source_repo_name}'.")
             return 1
        source_repo_info = source_repo_infos[0]
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
            "latest_tag": newest_tag
        }

        logger.info("--- Step 3: Analyzing Commits ---")
        commit_analyzer.analyze_all_repositories(
            all_repos_config, newest_id, next_newest_id
        )
        logger.info("Commit analysis completed.")

        logger.info("--- Step 4: Identifying Special Source Repositories ---")
        grt_repos_sources = _find_repos_by_name(all_repos_config, 'grt')
        alps_grt_path_suffix = 'alps/vendor/mediatek/proprietary/trustzone/grt'
        alps_grt_repo_source = _find_repo_by_path_suffix(all_repos_config, alps_grt_path_suffix)

        special_source_repo_infos: List[GitRepoInfo] = grt_repos_sources
        if alps_grt_repo_source and alps_grt_repo_source not in special_source_repo_infos:
             logger.info(f"Adding specific ALPS GRT repo ({alps_grt_path_suffix}) to special sources.")
             special_source_repo_infos.append(alps_grt_repo_source)
        logger.info(f"Identified {len(special_source_repo_infos)} potential special source repos.")

        logger.info("--- Step 5: Generating Patches ---")
        # Capture both returned maps
        special_commit_patch_map, patch_details_map = patch_generator.generate_patches(
            all_repos_config=all_repos_config,
            version_info=version_info,
            patch_config=patch_config,
            special_source_repo_infos=special_source_repo_infos
        )
        logger.info(f"Patch generation finished. Found {len(special_commit_patch_map)} special patches. Created map for {len(patch_details_map)} total patches.")

        logger.info("--- Step 6: Processing Nebula Mappings ---")
        nebula_child_to_special_map, special_commit_messages = _process_nebula_mappings(
            all_repos_config=all_repos_config,
            special_source_repo_infos=special_source_repo_infos,
            logger=logger
        )
        logger.info("Nebula mapping and special commit removal finished.")

        logger.info("--- Step 7: Linking Nebula Patches & Assigning Modules ---")
        patch_generator.link_nebula_patches(
            all_repos_config=all_repos_config,
            special_commit_patch_map=special_commit_patch_map,
            nebula_child_to_special_mapping=nebula_child_to_special_map,
            special_commit_messages=special_commit_messages
        )
        logger.info("Nebula patch linking finished.")

        logger.info("--- Step 7.5: Generating Excel Report ---")
        excel_success = False

        if excel_config and excel_config.enabled:
            logger.info("Excel reporting is enabled. Initializing reporter.")
            excel_reporter = ExcelReporter(logger, git_operator, excel_config)
            # Calculate absolute path for the report
            _target_excel_path_abs = os.path.abspath(os.path.join(".", excel_config.output_filename))
            logger.info(f"Target Excel file path: {_target_excel_path_abs}")

            # Call generate_report and store the result
            excel_success = excel_reporter.generate_report(
                all_repos_config=all_repos_config,
                version_info=version_info,
                target_excel_path=_target_excel_path_abs
            )

            if excel_success:
                logger.info("Excel report generated successfully.")
                generated_excel_file_path = _target_excel_path_abs # Store path only if successful
            else:
                logger.error("Excel report generation failed.")
                generated_excel_file_path = None # Ensure path is None on failure

        elif excel_config:
            logger.info("Excel reporting is configured but disabled.")
        else:
            logger.info("Excel reporting is not configured.")

        logger.info("--- Step 8: Packaging Release ---")
        package_success = False
        zip_filename = package_config.zip_name_template.format(
            project_name=package_config.project_name,
            latest_tag=version_info['latest_tag']
        )
        output_dir = "."
        output_zip_path = os.path.abspath(os.path.join(output_dir, zip_filename))

        package_success = release_packager.package_release(
            all_repos_config=all_repos_config,
            version_info=version_info,
            temp_patch_dir=patch_config.temp_patch_dir, # Pass temp dir (still used for logging in packager)
            package_config=package_config,
            output_zip_path=output_zip_path,
            patch_details_map=patch_details_map, # Pass the new map
            excel_config=excel_config, # Pass the excel config object
            generated_excel_path=generated_excel_file_path # Pass the path (or None)
        )

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
                    # return 1 # Optional critical failure
            else:
                logger.warning("No deployment configuration found (deploy_config). Skipping deployment.")
        else:
            logger.error("Packaging failed. Skipping deployment.")
            return 1

        logger.info("--- Final Commit Details (Post-Processing) ---")
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
                     msg_first_line = commit_detail.message.splitlines()[0] if commit_detail.message else ""
                     logger.debug(f"      Message: {msg_first_line}...")
             else:
                 logger.debug(f"  Commit Count: 0")
             logger.debug("-" * 20)

        logger.info("=========================================")
        logger.info("GR Release Automation Workflow Finished Successfully.")
        logger.info(f"Output package: {output_zip_path if package_success else 'N/A (Packaging Failed)'}")
        logger.info("=========================================")
        return 0

    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during the release workflow: {e}", exc_info=True)
        return 1

    finally:
        logger.info("--- Step 10: Cleanup ---")
        if patch_generator and patch_config:
            patch_generator.cleanup_temp_patches(patch_config)
        else:
            logger.warning("Cleanup skipped: PatchGenerator or PatchConfig not initialized.")

if __name__ == "__main__":
    sys.exit(main())
