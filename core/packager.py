import os
import zipfile
from typing import Dict, Optional, List # Added List
from logging import Logger

from config.schemas import AllReposConfig, PackageConfig, GitRepoInfo, CommitDetail, ExcelConfig
from utils.custom_logger import Logger as CustomLogger

class ReleasePackager:
    def __init__(self, logger: Logger):
        if not logger:
            raise ValueError("Logger instance is required")
        self.logger = logger

    def package_release(
        self,
        all_repos_config: AllReposConfig,
        version_info: Dict,
        temp_patch_dir: str, # Still potentially needed for context/debugging, but not for finding source paths
        package_config: PackageConfig,
        output_zip_path: str,
        patch_details_map: Dict[str, str], # New: Map relative arcname -> absolute source path
        excel_config: Optional[ExcelConfig],
        generated_excel_path: Optional[str]
    ) -> bool:
        self.logger.info(f"Starting release packaging process for output: {output_zip_path}")

        try:
            output_dir = os.path.dirname(output_zip_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self.logger.info(f"Created output directory: {output_dir}")

            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                self.logger.info(f"Opened ZIP file for writing: {output_zip_path}")
                packaged_files_count = 0
                missing_source_files = 0

                for repo_info in all_repos_config.all_git_repos():
                    if not repo_info.commit_details:
                        self.logger.debug(f"No commits found for {repo_info.repo_name}, skipping.")
                        continue

                    repo_log_name = f"{repo_info.repo_parent}/{repo_info.repo_name}" if repo_info.repo_parent else repo_info.repo_name
                    self.logger.debug(f"Checking commits for repo: {repo_log_name}")

                    for commit_detail in repo_info.commit_details:
                        if commit_detail.patch_path:
                            arcname = commit_detail.patch_path # This is the target path in the ZIP

                            # Find the actual source file path using the map
                            source_path = patch_details_map.get(arcname)

                            self.logger.debug(f"Attempting to add patch: Arcname='{arcname}', Expected Source='{source_path}'")

                            if source_path and os.path.exists(source_path):
                                zip_file.write(source_path, arcname=arcname)
                                packaged_files_count += 1
                                self.logger.debug(f"Added file to ZIP: {arcname}")
                            else:
                                # Log distinct error for missing source file, do not raise
                                missing_source_files += 1
                                if not source_path:
                                     self.logger.error(f"Source patch file path not found in patch_details_map for Arcname: {arcname}. Cannot add to ZIP.")
                                else: # source_path exists in map, but file not found on disk
                                     self.logger.error(f"Source patch file does not exist at the expected location: {source_path} (for Arcname: {arcname}). Cannot add to ZIP.")

                self.logger.info(f"Finished processing patch files. Added {packaged_files_count} files to the archive.")
                if missing_source_files > 0:
                     self.logger.warning(f"Could not find source files for {missing_source_files} patches. Check previous logs for details.")


                # --- Add Excel Report if generated ---
                if excel_config and excel_config.enabled and generated_excel_path:
                    self.logger.info(f"Checking for generated Excel file: {generated_excel_path}")
                    if os.path.exists(generated_excel_path):
                        excel_arcname = excel_config.output_filename # Use filename from config
                        self.logger.info(f"Adding Excel report to ZIP archive as: {excel_arcname}")
                        zip_file.write(generated_excel_path, arcname=excel_arcname)
                    else:
                        self.logger.warning(f"Excel report was enabled but file not found at {generated_excel_path}. Skipping inclusion in ZIP.")
                elif excel_config and excel_config.enabled:
                     self.logger.warning("Excel report was enabled, but no valid path provided (generation likely failed). Skipping inclusion in ZIP.")

            self.logger.info(f"Release package created successfully: {output_zip_path}")
            return True

        except (IOError, OSError, zipfile.BadZipFile) as e:
            self.logger.error(f"Failed to create or write to ZIP file {output_zip_path}: {e}", exc_info=True)
            if os.path.exists(output_zip_path):
                try:
                    os.remove(output_zip_path)
                    self.logger.info(f"Removed partially created/corrupted ZIP file: {output_zip_path}")
                except OSError as remove_err:
                    self.logger.error(f"Failed to remove corrupted ZIP file {output_zip_path}: {remove_err}")
            return False
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred during packaging: {e}", exc_info=True)
            return False