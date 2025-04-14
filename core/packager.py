import os
import zipfile
from typing import Dict
from logging import Logger # Correct import for Logger type hint

from config.schemas import AllReposConfig, PackageConfig, GitRepoInfo, CommitDetail
from utils.custom_logger import Logger as CustomLogger # Keep if needed elsewhere, but prefer type hint

class ReleasePackager:
    def __init__(self, logger: Logger):
        if not logger:
            raise ValueError("Logger instance is required")
        self.logger = logger

    def package_release(
        self,
        all_repos_config: AllReposConfig,
        version_info: Dict, # Expects 'latest_tag'
        temp_patch_dir: str,
        package_config: PackageConfig,
        output_zip_path: str # The full path including filename
    ) -> bool:
        """
        Collects generated patch files into a structured ZIP archive.

        Args:
            all_repos_config: Configuration containing repo info and commit details with patch paths.
            version_info: Dictionary containing the 'latest_tag'.
            temp_patch_dir: The base directory where temporary repo patch folders exist.
            package_config: Configuration for packaging details.
            output_zip_path: The full path where the final ZIP archive should be saved.

        Returns:
            True if packaging was successful, False otherwise.
        """
        self.logger.info(f"Starting release packaging process for output: {output_zip_path}")

        try:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_zip_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self.logger.info(f"Created output directory: {output_dir}")

            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                self.logger.info(f"Opened ZIP file for writing: {output_zip_path}")
                packaged_files_count = 0

                for repo_info in all_repos_config.all_git_repos():
                    if not repo_info.commit_details:
                        self.logger.debug(f"No commits found for {repo_info.repo_name}, skipping.")
                        continue

                    self.logger.debug(f"Checking commits for repo: {repo_info.repo_name} (Parent: {repo_info.repo_parent})")
                    for commit_detail in repo_info.commit_details:
                        if commit_detail.patch_path:
                            # commit_detail.patch_path already contains the desired relative path within the zip (arcname)
                            arcname = commit_detail.patch_path

                            # Construct the source path in the temporary directory structure
                            # Use slugified names for the temporary folder structure
                            repo_parent_slug = repo_info.repo_parent.replace('/', '_') if repo_info.repo_parent else 'no_parent'
                            repo_name_slug = repo_info.repo_name.replace('/', '_')
                            patch_filename = os.path.basename(arcname) # Get filename from the relative path

                            source_patch_file_path = os.path.join(
                                temp_patch_dir,
                                repo_parent_slug,
                                repo_name_slug,
                                patch_filename
                            )

                            self.logger.debug(f"Attempting to add patch: Source='{source_patch_file_path}', Arcname='{arcname}'")

                            if os.path.exists(source_patch_file_path):
                                zip_file.write(source_patch_file_path, arcname=arcname)
                                packaged_files_count += 1
                                self.logger.debug(f"Added file to ZIP: {arcname}")
                            else:
                                # Log an error if the source patch file is missing, but continue packaging others
                                self.logger.error(f"Source patch file not found, cannot add to ZIP: {source_patch_file_path} (Expected Arcname: {arcname})")
                        # else: # Log only if debugging is necessary
                            # self.logger.debug(f"Commit {commit_detail.id[:7]} in {repo_info.repo_name} has no patch_path. Skipping.")

                self.logger.info(f"Successfully added {packaged_files_count} patch files to the archive.")

            self.logger.info(f"Release package created successfully: {output_zip_path}")
            return True

        except (IOError, OSError, zipfile.BadZipFile) as e:
            self.logger.error(f"Failed to create or write to ZIP file {output_zip_path}: {e}", exc_info=True)
            # Attempt to clean up potentially corrupted zip file
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