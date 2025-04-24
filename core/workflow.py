import os
import shutil
from typing import List, Tuple, Optional, Dict, Any
from config.schemas import (
    CommitDetail, AllReposConfig, GitRepoInfo, RepoConfig, PatchConfig,
    PackageConfig, DeployConfig, ExcelConfig
)
from core.repo_manager import RepoManager
from utils.custom_logger import Logger
from utils.command_executor import CommandExecutor
from utils.git_utils import GitOperator
from core.commit_analyzer import CommitAnalyzer
from utils.tag_utils import extract_version_identifier, construct_tag
from core.patch_generator import PatchGenerator, SPECIAL_PATTERNS
from core.packager import ReleasePackager
from core.deployer import Deployer
from utils.excel_utils import ExcelReporter
from core.builder import BuildSystem
from core.git_tag_manager import GitTagFetcher
# Import RepoSynchronizer if it exists, otherwise handle potential absence
try:
    from core.sync.repo_synchronizer import RepoSynchronizer
except ImportError:
    RepoSynchronizer = None # Placeholder if sync module/class is not present

class ProjectWorkflow:

    def __init__(
        self,
        config: AllReposConfig,
        cmd_executor: CommandExecutor,
        git_operator: GitOperator,
        repo_manager: RepoManager,
        # synchronizer: Optional[RepoSynchronizer], # Make optional if RepoSynchronizer might not exist
        tag_fetcher: GitTagFetcher,
        builder: BuildSystem,
        analyzer: CommitAnalyzer,
        patch_generator: PatchGenerator,
        excel_reporter: ExcelReporter,
        packager: ReleasePackager,
        deployer: Deployer,
        logger: Logger,
        **kwargs: Any
    ) -> None:
        self.config: AllReposConfig = config
        self.cmd_executor: CommandExecutor = cmd_executor
        self.git_operator: GitOperator = git_operator
        self.repo_manager: RepoManager = repo_manager
        # self.synchronizer: Optional[RepoSynchronizer] = synchronizer
        self.tag_fetcher: GitTagFetcher = tag_fetcher
        self.builder: BuildSystem = builder
        self.analyzer: CommitAnalyzer = analyzer
        self.patch_generator: PatchGenerator = patch_generator
        self.excel_reporter: ExcelReporter = excel_reporter
        self.packager: ReleasePackager = packager
        self.deployer: Deployer = deployer
        self.logger: Logger = logger
        # Store other dependencies if passed via kwargs, though explicit is better
        self.other_dependencies: Dict[str, Any] = kwargs

    def _find_repos_by_name(self, repo_name: str) -> List[GitRepoInfo]:
        found_repos = [
            repo for repo in self.config.all_git_repos()
            if repo.repo_name == repo_name
        ]
        self.logger.debug(f"Found {len(found_repos)} repos with name='{repo_name}'.")
        return found_repos

    def _find_repo_by_path_suffix(self, path_suffix: str) -> Optional[GitRepoInfo]:
        normalized_suffix = path_suffix.replace('\\', '/')
        for repo in self.config.all_git_repos():
            if repo.repo_path and repo.repo_path.replace('\\', '/').endswith(normalized_suffix):
                self.logger.debug(f"Found repo by path suffix '{path_suffix}': {repo.repo_path}")
                return repo
        self.logger.debug(f"No repo found with path suffix '{path_suffix}'.")
        return None

    def _find_repos_by_parent(self, parent_name: str) -> List[GitRepoInfo]:
        found_repos = [
            repo for repo in self.config.all_git_repos()
            if repo.repo_parent == parent_name
        ]
        self.logger.debug(f"Found {len(found_repos)} repos with parent='{parent_name}'.")
        return found_repos

    def _identify_special_source_repos(self) -> List[GitRepoInfo]:
        self.logger.info("Identifying special source repositories (grt, specific alps path)...")
        grt_repos_sources = self._find_repos_by_name('grt')
        alps_grt_path_suffix = 'alps/vendor/mediatek/proprietary/trustzone/grt'
        alps_grt_repo_source = self._find_repo_by_path_suffix(alps_grt_path_suffix)

        special_source_repo_infos: List[GitRepoInfo] = grt_repos_sources
        if alps_grt_repo_source and alps_grt_repo_source not in special_source_repo_infos:
             self.logger.info(f"Adding specific ALPS GRT repo ({alps_grt_path_suffix}) to special sources.")
             special_source_repo_infos.append(alps_grt_repo_source)
        self.logger.info(f"Identified {len(special_source_repo_infos)} potential special source repos.")
        return special_source_repo_infos

    def _coordinate_nebula_mapping(
        self,
        special_source_repo_infos: List[GitRepoInfo],
        special_commit_patch_map: Dict[str, str]
    ) -> None:
        self.logger.info("Starting Nebula special commit identification, mapping, linking, and extraction process...")

        nebula_child_repos = self._find_repos_by_parent('nebula')
        if not nebula_child_repos:
            self.logger.warning("No child repositories found with parent 'nebula'. Skipping Nebula processing.")
            return

        if not special_source_repo_infos:
            self.logger.warning("No special source repositories identified. Cannot perform Nebula mapping.")
            return

        self.logger.info(f"Identified {len(special_source_repo_infos)} source repositories to scan for special commits.")
        self.logger.info(f"Found {len(nebula_child_repos)} Nebula child repositories.")

        special_commits_found: List[CommitDetail] = []
        source_repo_paths_with_special_commits: Dict[str, List[CommitDetail]] = {}

        for source_repo in special_source_repo_infos:
            repo_log_name = f"{source_repo.repo_parent}/{source_repo.repo_name}" if source_repo.repo_parent else source_repo.repo_name
            if not source_repo.commit_details:
                self.logger.debug(f"No commits to analyze in source repo {repo_log_name} (Path: {source_repo.repo_path})")
                continue

            found_in_repo = []
            for commit in source_repo.commit_details:
                if any(pattern in commit.message for pattern in SPECIAL_PATTERNS.values()):
                     self.logger.info(f"Found special commit in {repo_log_name} (Path: {source_repo.repo_path}): {commit.id[:7]}")
                     special_commits_found.append(commit)
                     found_in_repo.append(commit)

            if found_in_repo and source_repo.repo_path:
                 source_repo_paths_with_special_commits[source_repo.repo_path] = found_in_repo

        if not special_commits_found:
            self.logger.info("No special commits found in any designated source repository. Skipping Nebula mapping.")
            return

        special_commit_ids = [commit.id for commit in special_commits_found]
        special_commit_messages: Dict[str, str] = {commit.id: commit.message for commit in special_commits_found}
        nebula_child_to_special_map: Dict[str, List[str]] = {}

        self.logger.info(f"Building map for {len(nebula_child_repos)} Nebula child repos to {len(special_commit_ids)} special commits.")
        for nebula_child_repo in nebula_child_repos:
            if not nebula_child_repo.commit_details:
                continue
            for nebula_commit in nebula_child_repo.commit_details:
                nebula_child_to_special_map[nebula_commit.id] = special_commit_ids
                self.logger.debug(f"Mapped Nebula child {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}) -> {len(special_commit_ids)} special IDs.")

        self.logger.info("Linking Nebula patches using the generated maps...")
        self.patch_generator.link_nebula_patches(
            all_repos_config=self.config,
            special_commit_patch_map=special_commit_patch_map,
            nebula_child_to_special_mapping=nebula_child_to_special_map,
            special_commit_messages=special_commit_messages
        )
        self.logger.info("Nebula patch linking finished.")


        self.logger.info("Removing identified special commits from their source repositories...")
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
                 self.logger.info(f"Removed {removed_count} special commits from source repo {repo_log_name} (Path: {source_repo.repo_path})")

        self.logger.info(f"Finished Nebula processing. Mapped {len(nebula_child_to_special_map)} child commits. Removed special commits from sources.")


    def run_workflow(self) -> int:
        self.logger.info("========================================")
        self.logger.info("Starting GR Release Automation Workflow")
        self.logger.info("========================================")
        output_zip_path: Optional[str] = None
        generated_excel_file_path: Optional[str] = None

        try:
            patch_config: PatchConfig = self.config.patch_config
            package_config: PackageConfig = self.config.package_config
            deploy_config: Optional[DeployConfig] = self.config.deploy_config
            excel_config: Optional[ExcelConfig] = self.config.excel_config

            self.logger.info("--- Step 1: Repository Initialization ---")
            # Assuming RepoManager handles initialization in its constructor or a dedicated method called externally/previously
            # self.repo_manager.initialize_git_repos() # If needed here

            # Add Sync step if synchronizer is available
            # if self.synchronizer:
            #     self.logger.info("--- Step 1.5: Synchronizing Repositories ---")
            #     sync_success = self.synchronizer.synchronize_repositories()
            #     if not sync_success:
            #          self.logger.critical("Repository synchronization failed. Cannot proceed.")
            #          return 1
            #     self.logger.info("Repository synchronization completed.")
            # else:
            #     self.logger.info("--- Step 1.5: Synchronizing Repositories (Skipped - No Synchronizer) ---")


            self.logger.info("--- Step 2: Fetching Central Version Tags ---")
            source_repo_name = self.config.version_source_repo_name
            if not source_repo_name:
                self.logger.critical("Config Error: 'version_source_repo_name' missing.")
                return 1
            source_repo_infos = [r for r in self.config.all_git_repos() if r.repo_name == source_repo_name and r.repo_type == 'git']
            if not source_repo_infos:
                 self.logger.critical(f"Config Error: No source GitRepoInfo found for '{source_repo_name}'.")
                 return 1
            source_repo_info = source_repo_infos[0]
            if not source_repo_info.repo_path or not source_repo_info.local_branch:
                 self.logger.critical(f"Config Error: Path or branch missing for source repo '{source_repo_name}'.")
                 return 1

            newest_tag, next_newest_tag = self.tag_fetcher.fetch_latest_tags(
                repo_path=source_repo_info.repo_path,
                branch_name=source_repo_info.local_branch,
                remote_name=source_repo_info.remote_name or "origin",
                tag_prefix=source_repo_info.tag_prefix
            )
            if newest_tag is None or next_newest_tag is None:
                self.logger.critical(f"Tag fetch failed for source repo '{source_repo_name}'. Cannot proceed.")
                return 1
            self.logger.info(f"Source tags fetched: Newest='{newest_tag}', Next='{next_newest_tag}'")

            newest_id = extract_version_identifier(newest_tag, source_repo_info.tag_prefix)
            next_newest_id = extract_version_identifier(next_newest_tag, source_repo_info.tag_prefix)
            if newest_id is None or next_newest_id is None:
                self.logger.critical("Identifier extraction failed from source tags. Cannot proceed.")
                return 1
            self.logger.info(f"Global Version IDs: Newest='{newest_id}', Next='{next_newest_id}'")

            version_info: Dict[str, str] = {
                "newest_id": newest_id,
                "next_newest_id": next_newest_id,
                "latest_tag": newest_tag
            }

            # Add Build step if builder is available
            if self.builder:
                self.logger.info("--- Step 2.5: Executing Builds ---")
                # Determine which build types to run based on config or specific request if available
                build_success = self.builder.build()
                if not build_success:
                    self.logger.critical("Build process failed. Cannot proceed.")
                    return 1
                self.logger.info("Build process completed.")
            else:
                 self.logger.info("--- Step 2.5: Executing Builds (Skipped - No Builder) ---")

            # Handle Manual Merge Wait if applicable (logic needs clarification/config)
            self.logger.info("--- Step 2.7: Manual Merge Point (Placeholder) ---")
            # Add logic here if needed, e.g., wait for user input or check external state

            self.logger.info("--- Step 3: Analyzing Commits ---")
            self.analyzer.analyze_all_repositories(
                self.config, newest_id, next_newest_id
            )
            self.logger.info("Commit analysis completed.")

            self.logger.info("--- Step 4: Identifying Special Source Repositories ---")
            special_source_repo_infos = self._identify_special_source_repos()


            self.logger.info("--- Step 5: Generating Patches ---")
            special_commit_patch_map, patch_details_map = self.patch_generator.generate_patches(
                all_repos_config=self.config,
                version_info=version_info,
                patch_config=patch_config,
                special_source_repo_infos=special_source_repo_infos
            )
            self.logger.info(f"Patch generation finished. Found {len(special_commit_patch_map)} special patches. Created map for {len(patch_details_map)} total patches.")


            self.logger.info("--- Step 6 & 7: Processing Nebula Mappings & Linking ---")
            self._coordinate_nebula_mapping(
                 special_source_repo_infos=special_source_repo_infos,
                 special_commit_patch_map=special_commit_patch_map
            )
            # Note: Removed separate call to link_nebula_patches as it's integrated into _coordinate_nebula_mapping

            self.logger.info("--- Step 7.5: Generating Excel Report ---")
            excel_success = False
            if excel_config and excel_config.enabled:
                self.logger.info("Excel reporting is enabled.")
                _target_excel_path_abs = os.path.abspath(os.path.join(".", excel_config.output_filename))
                self.logger.info(f"Target Excel file path: {_target_excel_path_abs}")
                excel_success = self.excel_reporter.generate_report(
                    all_repos_config=self.config,
                    version_info=version_info,
                    target_excel_path=_target_excel_path_abs
                )
                if excel_success:
                    self.logger.info("Excel report generated successfully.")
                    generated_excel_file_path = _target_excel_path_abs
                else:
                    self.logger.error("Excel report generation failed.")
                    generated_excel_file_path = None
            elif excel_config:
                self.logger.info("Excel reporting is configured but disabled.")
            else:
                self.logger.info("Excel reporting is not configured.")


            self.logger.info("--- Step 8: Packaging Release ---")
            package_success = False
            zip_filename = package_config.zip_name_template.format(
                project_name=package_config.project_name,
                latest_tag=version_info['latest_tag']
            )
            output_dir = "."
            output_zip_path = os.path.abspath(os.path.join(output_dir, zip_filename))

            package_success = self.packager.package_release(
                all_repos_config=self.config,
                version_info=version_info,
                temp_patch_dir=patch_config.temp_patch_dir,
                package_config=package_config,
                output_zip_path=output_zip_path,
                patch_details_map=patch_details_map,
                excel_config=excel_config,
                generated_excel_path=generated_excel_file_path
            )

            if package_success:
                self.logger.info("--- Step 9: Deploying Package ---")
                if deploy_config:
                    self.logger.info(f"Deploying {output_zip_path} to {deploy_config.scp_user}@{deploy_config.scp_host}:{deploy_config.scp_remote_path}")
                    deploy_success = self.deployer.deploy_package(
                        local_zip_path=output_zip_path,
                        deploy_config=deploy_config
                    )
                    if deploy_success:
                        self.logger.info("Deployment completed successfully.")
                    else:
                        self.logger.error("Deployment failed.")
                        # Consider returning 1 if deployment failure is critical
                else:
                    self.logger.warning("No deployment configuration found (deploy_config). Skipping deployment.")
            else:
                self.logger.error("Packaging failed. Skipping deployment.")
                return 1

            self.logger.info("--- Final Commit Details (Post-Processing) ---")
            # Logging moved inside components or potentially reduced for brevity here
            # Add selective logging if still needed

            self.logger.info("=========================================")
            self.logger.info("GR Release Automation Workflow Finished Successfully.")
            self.logger.info(f"Output package: {output_zip_path if package_success else 'N/A (Packaging Failed)'}")
            self.logger.info("=========================================")
            return 0

        except Exception as e:
            self.logger.critical(f"An unexpected critical error occurred during the release workflow: {e}", exc_info=True)
            return 1

        # Note: Cleanup is handled in release.py's finally block