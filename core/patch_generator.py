import os
import re
import shutil
from typing import Dict, Optional, List, Tuple

from config.schemas import AllReposConfig, GitRepoInfo, CommitDetail, PatchConfig
from utils.git_utils import GitOperator
from utils.custom_logger import Logger
from utils.tag_utils import construct_tag
# Removed import of non-existent ensure_directory_exists


class PatchGenerator:
    def __init__(
        self,
        git_operator: GitOperator,
        logger: Logger
    ):
        if not git_operator:
            raise ValueError("GitOperator instance is required")
        if not logger:
            raise ValueError("Logger instance is required")
        self.git_operator = git_operator
        self.logger = logger

    # Removed _parse_commit_id_from_patch as it's no longer used.
    # Patch correlation is now done by order.
    def generate_patches(
        self,
        all_repos_config: AllReposConfig,
        version_info: Dict, # Expects keys like 'newest_id', 'next_newest_id'
        patch_config: PatchConfig,
        special_source_repo_infos: List[GitRepoInfo] # New parameter
    ) -> Dict[str, str]:
        """
        Generates patch files for all configured repositories, identifying special commits.

        Args:
            all_repos_config: The configuration object containing all repo info.
            version_info: Dictionary containing version identifiers ('newest_id', 'next_newest_id').
            patch_config: Configuration for patch generation (e.g., temp_patch_dir).
            special_source_repo_infos: List of GitRepoInfo objects for repos considered sources of special commits.

        Returns:
            A dictionary mapping special commit IDs to their final generated patch paths.
        """
        self.logger.info("Starting patch generation process...")
        temp_patch_dir = patch_config.temp_patch_dir
        special_commit_patch_map: Dict[str, str] = {} # special_commit_id -> final_relative_patch_path

        try:
            # Use os.makedirs directly
            os.makedirs(temp_patch_dir, exist_ok=True)
            self.logger.info(f"Ensured temporary patch directory exists: {temp_patch_dir}")
        except Exception as e:
            self.logger.critical(f"Failed to create or access temporary patch directory {temp_patch_dir}: {e}. Aborting patch generation.")
            return special_commit_patch_map # Return empty map on critical failure

        newest_id = version_info.get('newest_id')
        next_newest_id = version_info.get('next_newest_id')

        if not newest_id or not next_newest_id:
            self.logger.error("Missing 'newest_id' or 'next_newest_id' in version_info. Cannot generate patches.")
            return special_commit_patch_map

        # Define patterns for special commits (consistent with release.py)
        special_patterns = {
            "nebula-hyper": "] thyp-sdk: ",
            "nebula-sdk": "] nebula-sdk: ",
            "TEE": "] tee: ",
        }
        special_patterns_list = list(special_patterns.values()) # For easier checking

        # Create a set of paths for the special source repos for efficient lookup
        special_source_paths = {
            repo.repo_path.replace('\\', '/') for repo in special_source_repo_infos if repo.repo_path
        }
        self.logger.debug(f"Special source repo paths for patch check: {special_source_paths}")

        # Identify the specific yocto grt repo for exclusion (still relevant)
        yocto_grt_parent = 'yocto'
        yocto_grt_name = 'prebuilt/hypervisor/grt' # Assuming this is the name in manifest/config

        for repo_info in all_repos_config.all_git_repos():
            self.logger.debug(f"Processing repository: {repo_info.repo_name} (Parent: {repo_info.repo_parent})")

            # --- Skip Conditions ---
            if not repo_info.generate_patch:
                self.logger.debug(f"Skipping patch generation for {repo_info.repo_name}: generate_patch is False.")
                continue

            # Skip Nebula *child* repositories (parent is 'nebula')
            if repo_info.repo_parent == 'nebula':
                self.logger.info(f"Skipping patch generation for Nebula child repo: {repo_info.repo_name} (Parent: {repo_info.repo_parent})")
                continue

            # Skip specific yocto/prebuilt/hypervisor/grt
            if repo_info.repo_parent == yocto_grt_parent and repo_info.repo_name == yocto_grt_name:
                 self.logger.info(f"Skipping patch generation for excluded repo: {yocto_grt_parent}/{yocto_grt_name}")
                 continue

            # Check if repo_path is valid
            if not repo_info.repo_path or not os.path.isdir(repo_info.repo_path):
                self.logger.warning(f"Skipping patch generation for {repo_info.repo_name}: Invalid or missing repo_path '{repo_info.repo_path}'.")
                continue

            # REMOVED: Check for relative_path_in_parent is None.
            # We should attempt patch generation even for top-level manifest repos if configured.
            # The path calculation below should handle None or empty string correctly.


            # --- Determine Refs ---
            try:
                start_ref = construct_tag(repo_info.tag_prefix, next_newest_id)
                end_ref = construct_tag(repo_info.tag_prefix, newest_id)
                self.logger.debug(f"Constructed tags for {repo_info.repo_name}: {start_ref}..{end_ref}")
            except ValueError as e:
                self.logger.error(f"Error constructing tags for {repo_info.repo_name}: {e}. Skipping patch generation.")
                continue

            # --- Generate Patches ---
            # Create a sub-directory within the temp dir specific to this repo to avoid filename clashes if repo names collide across parents
            repo_temp_patch_subdir = os.path.join(temp_patch_dir, repo_info.repo_parent.replace('/', '_'), repo_info.repo_name.replace('/', '_'))
            # Use os.makedirs directly
            os.makedirs(repo_temp_patch_subdir, exist_ok=True)

            generated_patch_paths = self.git_operator.format_patch(
                repository_path=repo_info.repo_path,
                start_ref=start_ref,
                end_ref=end_ref,
                output_dir=repo_temp_patch_subdir # Use repo-specific subdir
            )

            if not generated_patch_paths:
                self.logger.warning(f"No patch files generated or returned by format_patch for {repo_info.repo_name} in range {start_ref}..{end_ref}.")
                continue

            # --- Process Generated Patches by Order ---
            self.logger.info(f"Processing {len(generated_patch_paths)} generated patches for {repo_info.repo_name} by correlating order...")

            # 1. Sort generated patch paths numerically by sequence number
            def sort_key(path: str) -> int:
                filename = os.path.basename(path)
                match = re.match(r'^(\d{4})-.*\.patch$', filename)
                if match:
                    return int(match.group(1))
                self.logger.warning(f"Could not extract sequence number from patch filename: {filename}. Assigning high sort value.")
                return 9999 # Place improperly named files at the end
            sorted_patch_paths = sorted(generated_patch_paths, key=sort_key)

            # 2. Retrieve ordered commit details (assuming CommitAnalyzer provides them in order)
            ordered_commits = repo_info.commit_details if repo_info.commit_details else []

            # 3. Strict Length Validation
            if len(sorted_patch_paths) != len(ordered_commits):
                self.logger.critical(
                    f"CRITICAL MISMATCH: Number of sorted patch files ({len(sorted_patch_paths)}) "
                    f"does not match number of commits ({len(ordered_commits)}) for repository "
                    f"'{repo_info.repo_name}' in range {start_ref}..{end_ref}. "
                    f"This indicates a failure in the 1:1 correlation assumption. "
                    f"Skipping patch processing for this repository."
                )
                # Optionally, list files and commits for debugging
                # self.logger.debug(f"Sorted Patches: {[os.path.basename(p) for p in sorted_patch_paths]}")
                # self.logger.debug(f"Ordered Commits: {[c.id[:7] for c in ordered_commits]}")
                continue # Skip to the next repository

            self.logger.debug(f"Successfully matched {len(sorted_patch_paths)} patches to {len(ordered_commits)} commits for {repo_info.repo_name}.")

            # 4. Iterate using zip to correlate patch path and commit detail
            for patch_file_path, commit_detail in zip(sorted_patch_paths, ordered_commits):
                patch_filename = os.path.basename(patch_file_path)
                commit_id = commit_detail.id # Use commit ID directly from the CommitDetail object

                # Calculate the final relative path for the ZIP archive
                # Filter out None or empty strings from path components
                path_parts = [
                    repo_info.repo_parent,
                    repo_info.relative_path_in_parent,
                    patch_filename # Use the actual patch filename
                ]
                # Use "/".join with filter to handle potential None/empty parts and ensure '/' separator
                final_relative_patch_path = "/".join(filter(None, [p.replace('\\', '/') if p else None for p in path_parts]))

                # Store the final relative path in the CommitDetail
                # This will apply to *all* commits, including Nebula children,
                # which will be correctly handled by link_nebula_patches later.
                commit_detail.patch_path = final_relative_patch_path
                self.logger.debug(f"Assigned patch path '{final_relative_patch_path}' to commit {commit_id[:7]} in {repo_info.repo_name} based on order.")

                # --- Check if this commit is "special" (using the current commit_detail) ---
                # Condition 1: Is the repo path in the list of special source paths?
                repo_path_normalized = repo_info.repo_path.replace('\\', '/') if repo_info.repo_path else None
                is_from_special_source = repo_path_normalized in special_source_paths

                # Condition 2: Does the commit message contain any special pattern?
                has_special_pattern = any(p in commit_detail.message for p in special_patterns_list)

                is_special = is_from_special_source and has_special_pattern

                if is_special:
                    # Store the mapping: special commit ID -> final *relative* patch path
                    # This map is used by link_nebula_patches
                    special_commit_patch_map[commit_id] = final_relative_patch_path
                    self.logger.info(f"Recorded special commit patch mapping (by order): {commit_id[:7]} -> {final_relative_patch_path}")
        self.logger.info(f"Finished generating patches. Found {len(special_commit_patch_map)} special commit patches to potentially link to Nebula.")
        return special_commit_patch_map


    def link_nebula_patches(
        self,
        all_repos_config: AllReposConfig,
        special_commit_patch_map: Dict[str, str], # Map: special_commit_id -> final_relative_patch_path
        nebula_child_to_special_mapping: Dict[str, List[str]] # Map: nebula_child_commit_id -> [special_commit_id, ...]
    ):
        """Links Nebula commits to the generated patches of their associated special commits."""
        """Links Nebula child commits to the generated patches of their associated special commits."""
        self.logger.info("Starting Nebula child patch linking process...")

        # Find all Nebula child repos (parent is 'nebula')
        nebula_child_repos = [
            repo for repo in all_repos_config.all_git_repos()
            if repo.repo_parent == 'nebula'
        ]

        if not nebula_child_repos:
            self.logger.warning("No Nebula child repositories found (parent='nebula'). Skipping patch linking.")
            return
        # Check required maps early
        if not special_commit_patch_map:
            self.logger.info("No special commit patches were generated or mapped. Skipping Nebula linking.")
            return
        if not nebula_child_to_special_mapping:
            self.logger.info("No mapping provided between Nebula child commits and special commits. Skipping Nebula linking.")
            return


        linked_count = 0
        unlinked_commits = 0

        # Iterate through each Nebula child repo found
        for nebula_child_repo in nebula_child_repos:
            self.logger.debug(f"Processing links for Nebula child repo: {nebula_child_repo.repo_name}")
            if not nebula_child_repo.commit_details:
                self.logger.debug(f"Nebula child repo {nebula_child_repo.repo_name} has no commits in range. Skipping.")
                continue

            # Iterate through commits in this Nebula child repo
            for nebula_commit in nebula_child_repo.commit_details:
                associated_patch_path = None # Reset for each nebula commit
                special_commit_ids = nebula_child_to_special_mapping.get(nebula_commit.id, [])

                if not special_commit_ids:
                    self.logger.debug(f"Nebula child commit {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}) has no associated special commits in the map.")
                    nebula_commit.patch_path = None # Explicitly set to None
                    unlinked_commits += 1
                    continue

                # Find the *first* special commit ID that has a patch in the map
                for special_commit_id in special_commit_ids:
                    patch_path = special_commit_patch_map.get(special_commit_id)
                    if patch_path:
                        associated_patch_path = patch_path
                        self.logger.debug(f"Found patch path '{patch_path}' from special commit {special_commit_id[:7]} for Nebula child commit {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}).")
                        break # Stop after finding the first one
                    else:
                         self.logger.debug(f"Special commit {special_commit_id[:7]} linked to {nebula_commit.id[:7]}, but no patch path found in special_commit_patch_map.")

                # Assign the first found path (or None if none were found)
                nebula_commit.patch_path = associated_patch_path

                if associated_patch_path:
                    linked_count += 1
                    self.logger.info(f"Linked patch '{associated_patch_path}' to Nebula child commit {nebula_commit.id[:7]} ({nebula_child_repo.repo_name})")
                else:
                    self.logger.warning(f"Nebula child commit {nebula_commit.id[:7]} ({nebula_child_repo.repo_name}) had associated special commit IDs ({[sid[:7] for sid in special_commit_ids]}), but none had a resolvable patch path in the map.")
                    unlinked_commits +=1

        self.logger.info(f"Finished Nebula child patch linking. Successfully linked patches for {linked_count} Nebula child commits. Could not resolve links for {unlinked_commits} commits.")

    def cleanup_temp_patches(self, patch_config: PatchConfig):
        """Removes the temporary patch directory."""
        temp_patch_dir = patch_config.temp_patch_dir
        if os.path.isdir(temp_patch_dir):
            try:
                shutil.rmtree(temp_patch_dir)
                self.logger.info(f"Successfully removed temporary patch directory: {temp_patch_dir}")
            except Exception as e:
                self.logger.error(f"Failed to remove temporary patch directory {temp_patch_dir}: {e}")
        else:
            self.logger.debug(f"Temporary patch directory {temp_patch_dir} not found, skipping cleanup.")