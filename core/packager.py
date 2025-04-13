import os
import zipfile
from typing import Dict
from logging import Logger
from config.schemas import (
    AllReposConfig,
    CommitDetail,
    PackageConfig,
    GitRepoInfo
)

class ReleasePackager:
    def __init__(self, logger: Logger):
        self.logger: Logger = logger

    def package_release(
        self,
        all_repos_config: AllReposConfig,
        version_info: Dict,
        temp_patch_dir: str,
        package_config: PackageConfig,
        output_zip_path: str
    ) -> bool:
        self.logger.info(f"Starting release packaging for {output_zip_path}")
        try:
            with zipfile.ZipFile(
                output_zip_path, 'w', zipfile.ZIP_DEFLATED
            ) as zip_file:
                self.logger.info(
                    f"Successfully opened ZIP archive: {output_zip_path}"
                )
                for repo_info in all_repos_config.all_git_repos():
                    for commit_detail in repo_info.commit_details:
                        if not commit_detail.patch_path:
                            continue

                        repo_parent_slug = repo_info.repo_parent.replace(
                            '/', '_'
                        )
                        repo_name_slug = repo_info.repo_name.replace('/', '_')
                        patch_filename = os.path.basename(
                            commit_detail.patch_path
                        )
                        source_patch_file_path = os.path.join(
                            temp_patch_dir,
                            repo_parent_slug,
                            repo_name_slug,
                            patch_filename
                        )

                        archive_path = commit_detail.patch_path

                        self.logger.debug(
                            f"Attempting to add patch: "
                            f"Source='{source_patch_file_path}', "
                            f"Archive='{archive_path}'"
                        )

                        if not os.path.isfile(source_patch_file_path):
                            self.logger.error(
                                f"Temporary patch file not found: "
                                f"{source_patch_file_path}. Skipping."
                            )
                            continue

                        try:
                            zip_file.write(
                                source_patch_file_path, arcname=archive_path
                            )
                            self.logger.info(
                                f"Added patch to archive: {archive_path}"
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to add {archive_path} to zip: {e}"
                            )

                self.logger.info(
                    f"Completed packaging release to {output_zip_path}"
                )
            return True
        except (IOError, zipfile.BadZipFile, OSError) as e:
            self.logger.error(
                f"Critical error creating/writing ZIP file "
                f"{output_zip_path}: {e}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during packaging: {e}"
            )
            return False