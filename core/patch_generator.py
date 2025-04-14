import os
import re
import shutil
from typing import Dict, Optional, List, Tuple, Set # Added Set

from config.schemas import AllReposConfig, GitRepoInfo, CommitDetail, PatchConfig
from utils.git_utils import GitOperator
from utils.custom_logger import Logger
from utils.tag_utils import construct_tag

# Define special patterns globally for consistency
SPECIAL_PATTERNS: Dict[str, str] = {
    "nebula-hyper": "] thyp-sdk: ",
    "nebula-sdk": "] nebula-sdk: ",
    "TEE": "] tee: ",
}
SPECIAL_PATTERNS_LIST: List[str] = list(SPECIAL_PATTERNS.values())

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

    def generate_patches(
        self,
        all_repos_config: AllReposConfig,
        version_info: Dict, # Expects 'newest_id', 'next_newest_id'
        patch_config: PatchConfig,
        special_source_repo_infos: List[GitRepoInfo] # Passed from release.py
    ) -> Dict[str, str]:
        """
        Generates patch files using 'git format-patch' for eligible repositories,
        correlates them with commit details by order, assigns relative patch paths,
        and identifies special commits, returning a map of their IDs to patch paths.

        IMPORTANT: This function expects 'all_repos_config' to contain commit details
                   *before* any special commits have been removed by other processes
                   (like _process_nebula_mappings in release.py).

        Args:
            all_repos_config: The configuration containing all repo info and UNMODIFIED commit details.
            version_info: Dictionary containing 'newest_id' and 'next_newest_id'.
            patch_config: Configuration for patch generation (e.g., temp_patch_dir).
            special_source_repo_infos: List of GitRepoInfo for repos considered sources of special commits.

        Returns:
            A dictionary mapping special commit IDs to their final generated relative patch paths.
            Returns an empty dictionary if critical errors occur (e.g., temp dir creation failure).
        """
        self.logger.info("Starting patch generation process...")
        temp_patch_dir = patch_config.temp_patch_dir
        special_commit_patch_map: Dict[str, str] = {} # special_commit_id -> final_relative_patch_path

        # --- 1. Prepare Temporary Directory ---
        try:
            os.makedirs(temp_patch_dir, exist_ok=True)
            self.logger.info(f"Ensured temporary patch directory exists: {temp_patch_dir}")
        except OSError as e:
            self.logger.critical(f"Failed to create or access temporary patch directory {temp_patch_dir}: {e}. Aborting patch generation.")
            return special_commit_patch_map # Return empty map

        # --- 2. Get Version IDs ---
        newest_id = version_info.get('newest_id')
        next_newest_id = version_info.get('next_newest_id')
        if not newest_id or not next_newest_id:
            self.logger.error("Missing 'newest_id' or 'next_newest_id' in version_info. Cannot generate patches.")
            return special_commit_patch_map

        # --- 3. Identify Special Source Repos ---
        special_source_paths: Set[str] = {
            repo.repo_path.replace('\\', '/') for repo in special_source_repo_infos if repo.repo_path
        }
        self.logger.debug(f"Special source repo paths for patch check: {special_source_paths}")

        # --- 4. Define Exclusion ---
        # Specific repo to exclude from patch generation (matches requirement)
        excluded_repo_parent = 'yocto'
        excluded_repo_name = 'prebuilt/hypervisor/grt'

        # --- 5. Iterate Through Repositories ---
        for repo_info in all_repos_config.all_git_repos():
            repo_log_name = f"{repo_info.repo_parent}/{repo_info.repo_name}" if repo_info.repo_parent else repo_info.repo_name
            self.logger.debug(f"Processing repository: {repo_log_name} (Path: {repo_info.repo_path})")

            # --- 5a. Skip Conditions ---
            if not repo_info.generate_patch:
                self.logger.debug(f"Skipping {repo_log_name}: generate_patch is False.")
                continue
            if repo_info.repo_parent == 'nebula':
                self.logger.info(f"Skipping Nebula child repo: {repo_log_name}")
                continue
            if repo_info.repo_parent == excluded_repo_parent and repo_info.repo_name == excluded_repo_name:
                 self.logger.info(f"Skipping explicitly excluded repo: {excluded_repo_parent}/{excluded_repo_name}")
                 continue
            if not repo_info.repo_path or not os.path.isdir(repo_info.repo_path):
                self.logger.warning(f"Skipping {repo_log_name}: Invalid or missing repo_path '{repo_info.repo_path}'.")
                continue

            # --- 5b. Determine Refs ---
            try:
                start_ref = construct_tag(repo_info.tag_prefix, next_newest_id)
                end_ref = construct_tag(repo_info.tag_prefix, newest_id)
                self.logger.debug(f"Refs for {repo_log_name}: {start_ref}..{end_ref}")
            except ValueError as e:
                self.logger.error(f"Error constructing tags for {repo_log_name}: {e}. Skipping.")
                continue

            # --- 5c. Create Repo-Specific Temp Subdir ---
            repo_parent_slug = repo_info.repo_parent.replace('/', '_') if repo_info.repo_parent else 'no_parent'
            repo_name_slug = repo_info.repo_name.replace('/', '_')
            repo_temp_patch_subdir = os.path.join(temp_patch_dir, repo_parent_slug, repo_name_slug)
            try:
                os.makedirs(repo_temp_patch_subdir, exist_ok=True)
            except OSError as e:
                self.logger.error(f"Failed to create repo temp subdir {repo_temp_patch_subdir} for {repo_log_name}: {e}. Skipping.")
                continue

            # --- 5d. Generate Patches using GitOperator ---
            generated_patch_paths = self.git_operator.format_patch(
                repository_path=repo_info.repo_path,
                start_ref=start_ref,
                end_ref=end_ref,
                output_dir=repo_temp_patch_subdir
            )

            if not generated_patch_paths:
                self.logger.warning(f"No patch files generated by format_patch for {repo_log_name} in range {start_ref}..{end_ref}. This might be expected if there are no commits.")
                # Check commit details - if they exist but no patches were made, it's potentially an issue
                if repo_info.commit_details:
                    self.logger.warning(f"Commit details exist for {repo_log_name} but no patches were generated. Check Git history and refs.")
                continue # Continue to next repo

            # --- 5e. Correlate Patches and Commits by Order (CRITICAL FIX) ---
            self.logger.info(f"Correlating {len(generated_patch_paths)} generated patches for {repo_log_name}...")

            # Sort generated patch paths numerically (0001, 0002, ...)
            def sort_key(path: str) -> int:
                filename = os.path.basename(path)
                match = re.match(r'^(\d{4})-.*\.patch$', filename)
                return int(match.group(1)) if match else 9999
            try:
                sorted_patch_paths = sorted(generated_patch_paths, key=sort_key)
                # Basic check for unexpected filenames after sort
                if any(sort_key(p) == 9999 for p in sorted_patch_paths):
                     self.logger.warning(f"Found patches with unexpected filenames in {repo_temp_patch_subdir}. Correlation might be affected.")
            except Exception as e:
                self.logger.error(f"Error sorting patch files for {repo_log_name}: {e}. Skipping correlation for this repo.")
                continue

            # Retrieve ORDERED commit details (MUST be from the unmodified list)
            ordered_commits = repo_info.commit_details if repo_info.commit_details else []

            # **VALIDATION:** Check if counts match
            if len(sorted_patch_paths) != len(ordered_commits):
                self.logger.critical(
                    f"CRITICAL MISMATCH in {repo_log_name}: "
                    f"Patches generated ({len(sorted_patch_paths)}) != Commits found ({len(ordered_commits)}) "
                    f"for range {start_ref}..{end_ref}. "
                    f"Patch/commit correlation failed. Skipping patch assignment for this repo."
                    # Optional verbose logging:
                    # f"\n  Patches: {[os.path.basename(p) for p in sorted_patch_paths]}"
                    # f"\n  Commits: {[c.id[:7] for c in ordered_commits]}"
                )
                continue # Skip to the next repository

            self.logger.debug(f"Count matched for {repo_log_name}: {len(sorted_patch_paths)} patches/commits.")

            # --- 5f. Assign Paths and Identify Special Commits ---
            for i, (patch_file_path, commit_detail) in enumerate(zip(sorted_patch_paths, ordered_commits)):
                patch_filename = os.path.basename(patch_file_path)

                # Calculate final relative path (for ZIP archive structure)
                path_parts = [
                    repo_info.repo_parent,
                    repo_info.relative_path_in_parent,
                    patch_filename
                ]
                # Use "/" separator, filter None/empty parts
                final_relative_patch_path = "/".join(filter(None, [p.replace('\\', '/') if p else None for p in path_parts]))

                # Store the final relative path in the CommitDetail
                commit_detail.patch_path = final_relative_patch_path
                self.logger.debug(f"  [#{i+1}] Commit {commit_detail.id[:7]} -> Patch '{patch_filename}' -> Assigned Path: '{final_relative_patch_path}'")

                # Check if this commit is "special"
                repo_path_normalized = repo_info.repo_path.replace('\\', '/') if repo_info.repo_path else None
                is_from_special_source = repo_path_normalized in special_source_paths
                has_special_pattern = any(p in commit_detail.message for p in SPECIAL_PATTERNS_LIST)

                if is_from_special_source and has_special_pattern:
                    special_commit_patch_map[commit_detail.id] = final_relative_patch_path
                    self.logger.info(f"  Identified special commit: {commit_detail.id[:7]} ({repo_log_name}). Mapped to patch: '{final_relative_patch_path}'")

        self.logger.info(f"Finished generating patches. Found {len(special_commit_patch_map)} special commit patches.")
        return special_commit_patch_map


    def link_nebula_patches(
        self,
        all_repos_config: AllReposConfig,
        special_commit_patch_map: Dict[str, str], # Map: special_commit_id -> final_relative_patch_path
        nebula_child_to_special_mapping: Dict[str, List[str]], # Map: nebula_child_commit_id -> [special_commit_id, ...]
        # TODO: This function needs access to the messages of the special commits.
        #       Refactor release.py:_process_nebula_mappings to provide this map.
        special_commit_messages: Dict[str, str] # Map: special_commit_id -> message
    ):
        """
        Links Nebula child commits to the generated patches of their associated special commits
        and determines their 'commit_module' based on *all* linked special commits' messages.

        Updates 'patch_path' and 'commit_module' in the CommitDetail objects for Nebula
        child repositories within 'all_repos_config' in-place.

        Args:
            all_repos_config: The configuration object (potentially modified by release.py).
            special_commit_patch_map: Map of special commit IDs to their generated relative patch paths.
            nebula_child_to_special_mapping: Map linking Nebula child commit IDs to lists of special commit IDs.
            special_commit_messages: Map of special commit IDs to their full commit messages.
                                     **(Needs to be provided by the caller - see TODO above)**.
        """
        self.logger.info("Starting Nebula child patch linking and module assignment...")

        if not special_commit_patch_map:
            self.logger.info("No special commit patches were mapped. Skipping Nebula linking.")
            return
        if not nebula_child_to_special_mapping:
            self.logger.info("No mapping provided between Nebula child commits and special commits. Skipping Nebula linking.")
            return
        if not special_commit_messages:
             self.logger.warning("Missing special_commit_messages map. Cannot determine commit modules for Nebula children.")
             # Proceed with path linking only, modules will be None/empty.

        linked_count = 0
        unlinked_commits = 0
        module_assigned_count = 0

        # Iterate through Nebula child repos (parent is 'nebula')
        for repo_info in all_repos_config.all_git_repos():
            if repo_info.repo_parent != 'nebula':
                continue

            repo_log_name = f"nebula/{repo_info.repo_name}"
            self.logger.debug(f"Processing links for Nebula child repo: {repo_log_name}")

            if not repo_info.commit_details:
                self.logger.debug(f"{repo_log_name} has no commits in range. Skipping.")
                continue

            for nebula_commit in repo_info.commit_details:
                linked_patch_path: Optional[str] = None # Reset for each nebula commit
                modules: Set[str] = set() # Use set for unique module names

                special_commit_ids = nebula_child_to_special_mapping.get(nebula_commit.id, [])

                if not special_commit_ids:
                    self.logger.debug(f"Nebula commit {nebula_commit.id[:7]} ({repo_log_name}) has no associated special commits.")
                    nebula_commit.patch_path = None # Explicitly set to None
                    nebula_commit.commit_module = None # Ensure module is None
                    unlinked_commits += 1
                    continue

                # Iterate through ALL associated special commits to link path (first found) and gather modules (all found)
                first_link_found = False
                for special_commit_id in special_commit_ids:
                    # 1. Link Patch Path (from first match)
                    if not first_link_found:
                        patch_path = special_commit_patch_map.get(special_commit_id)
                        if patch_path:
                            linked_patch_path = patch_path
                            first_link_found = True
                            self.logger.debug(f"  Found patch link for {nebula_commit.id[:7]}: '{patch_path}' (from Special Commit {special_commit_id[:7]})")

                    # 2. Gather Modules (from all matches)
                    if special_commit_messages:
                        special_message = special_commit_messages.get(special_commit_id)
                        if special_message:
                            for module_name, pattern in SPECIAL_PATTERNS.items():
                                if pattern in special_message:
                                    if module_name not in modules:
                                        modules.add(module_name)
                                        self.logger.debug(f"  Added module '{module_name}' for {nebula_commit.id[:7]} (from Special Commit {special_commit_id[:7]})")
                                    # No break here, collect all modules from all linked commits
                        else:
                            self.logger.warning(f"  Message not found for special commit {special_commit_id[:7]} while checking modules for {nebula_commit.id[:7]}.")
                    # else: handled by initial check


                # Assign the final results
                nebula_commit.patch_path = linked_patch_path
                nebula_commit.commit_module = sorted(list(modules)) if modules else None # Assign sorted list or None

                if linked_patch_path:
                    linked_count += 1
                    self.logger.info(f"Linked patch '{linked_patch_path}' to Nebula commit {nebula_commit.id[:7]} ({repo_log_name})")
                else:
                    unlinked_commits += 1
                    self.logger.warning(f"Nebula commit {nebula_commit.id[:7]} ({repo_log_name}) had special IDs ({[sid[:7] for sid in special_commit_ids]}) but none had a patch path.")

                if nebula_commit.commit_module:
                    module_assigned_count += 1
                    self.logger.info(f"Assigned modules {nebula_commit.commit_module} to Nebula commit {nebula_commit.id[:7]} ({repo_log_name})")
                elif special_commit_messages: # Only log if messages were expected
                     self.logger.debug(f"No relevant modules found for Nebula commit {nebula_commit.id[:7]} ({repo_log_name}) based on linked special commits.")


        self.logger.info(f"Finished Nebula linking. Linked paths for {linked_count} commits. Failed path links for {unlinked_commits} commits. Assigned modules for {module_assigned_count} commits.")


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