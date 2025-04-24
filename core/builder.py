import os
import pathlib
import shlex
import shutil
import subprocess
from dataclasses import asdict
from typing import List, Dict, Optional, Any, Tuple
from config.schemas import BuildConfig, BuildTypeConfig, FileCopyOperation, BuildGitConfig, AllReposConfig, GitRepoInfo # Added AllReposConfig, GitRepoInfo
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from utils.file_utils import FileOperator
from utils.git_utils import GitOperator


class BuildSystem:
    def __init__(self, build_config: BuildConfig, command_executor: CommandExecutor, all_repos_config: AllReposConfig) -> None: # Added all_repos_config
        self.config: BuildConfig = build_config
        self.command_executor: CommandExecutor = command_executor
        self.all_repos_config: AllReposConfig = all_repos_config # Store all_repos_config
        self.logger: Logger = Logger(name=self.__class__.__name__)
        self.file_operator: FileOperator = FileOperator()
        self.git_operator: GitOperator = GitOperator(command_executor)

        # Path definitions remain the same...
        self.grpower_path: pathlib.Path = pathlib.Path("~/grpower/").expanduser()
        self.thyp_sdk_path: pathlib.Path = pathlib.Path(self.config.paths.thyp_sdk_path).expanduser()
        self.nebula_sdk_output_path: pathlib.Path = pathlib.Path(self.config.paths.nebula_sdk_output).expanduser()
        self.prebuilt_images_path: pathlib.Path = pathlib.Path(self.config.paths.prebuilt_images).expanduser()
        self.nebula_out_path: pathlib.Path = pathlib.Path(self.config.paths.nebula_out).expanduser()
        self.tee_temp_path: pathlib.Path = pathlib.Path(self.config.paths.tee_temp).expanduser()
        self.tee_kernel_path: pathlib.Path = pathlib.Path(self.config.paths.tee_kernel).expanduser()
        self.yocto_hypervisor_path: pathlib.Path = pathlib.Path(self.config.paths.yocto_hypervisor).expanduser()


    def clean_environment(self) -> None:
        if not self.config.enable_environment_cleanup:
            self.logger.info("Environment cleanup disabled, skipping...")
            return

        paths_to_clean: List[Tuple[str, List[str]]] = [
            (self.config.paths.grpower_workspace, ["buildroot-pvt8675/", "nebula-ree/", "buildroot-pvt8675_tee/"]),
            (str(self.nebula_out_path), [""])
        ]

        for base_path_str, subpaths in paths_to_clean:
            expanded_base = pathlib.Path(base_path_str).expanduser()
            for subpath in subpaths:
                full_path = expanded_base / subpath
                self.logger.info(f"Cleaning path: {full_path}")
                self.file_operator.remove_directory_recursive(str(full_path))


    def _get_environment_after_sourcing(self, script_path: pathlib.Path, cwd: pathlib.Path) -> Dict[str, str]:
        env_vars: Dict[str, str] = {}
        command_str = f"export NO_PIPENV_SHELL=1 && source {shlex.quote(str(script_path))} && env"
        self.logger.debug(f"Attempting to capture environment using command in {cwd}: {command_str}")
        try:
            process_result = self.command_executor._run_subprocess(
                 command=command_str,
                 cwd=cwd,
                 shell=True,
                 capture_output=True,
                 text=True,
                 check=True
             )

            if process_result.stdout:
                for line in process_result.stdout.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if '=' not in line or line.startswith('#') or line.startswith('export'):
                        continue
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        # Basic filtering, might need refinement
                        if key.isidentifier() and not key.startswith('_') and '(' not in key:
                           env_vars[key] = value
            else:
                 self.logger.warning(f"No stdout received from environment capture command: '{command_str}' in {cwd}")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Failed to execute or find command for environment capture from {script_path.name} in {cwd}: {e}")
            raise RuntimeError(f"Failed to capture environment from script {script_path.name}") from e
        except Exception as e:
             self.logger.exception(f"Unexpected error capturing environment from {script_path.name} in {cwd}: {e}")
             raise RuntimeError(f"Unexpected error capturing environment from script {script_path.name}") from e

        if not env_vars:
             self.logger.warning(f"Captured environment from {script_path.name} appears empty.")

        self.logger.info(f"Successfully captured {len(env_vars)} environment variables from {script_path.name}")
        return env_vars

    def _get_environment_after_script_execution(
        self,
        script_path: pathlib.Path,
        script_args: List[str],
        cwd: pathlib.Path,
        base_env: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        env_vars: Dict[str, str] = {}
        script_name: str = script_path.name
        quoted_cwd: str = shlex.quote(str(cwd))
        # Ensure script is executed relative to cwd if it's in cwd
        if script_path.parent == cwd:
            quoted_script: str = f"./{shlex.quote(script_name)}"
        else:
             quoted_script: str = shlex.quote(str(script_path))

        joined_args: str = shlex.join(script_args)

        # Simplified command structure
        command_str: str = f"{quoted_script} {joined_args} && env"

        self.logger.debug(f"Attempting script execution and environment capture in {cwd}: {command_str}")

        try:
            process_result = self.command_executor._run_subprocess(
                command=command_str,
                cwd=cwd,
                shell=True, # Shell=True needed for '&&'
                capture_output=True,
                text=True,
                check=True,
                env=base_env
            )

            if process_result.stdout:
                env_output_lines = process_result.stdout.strip().splitlines()
                # Find the start of the 'env' output (crude heuristic)
                env_start_index = -1
                for i, line in enumerate(env_output_lines):
                     if '=' in line and line.strip() == line and not line.startswith('#'): # Likely env output
                         env_start_index = i
                         break

                if env_start_index != -1:
                    for line in env_output_lines[env_start_index:]:
                        line = line.strip()
                        if not line:
                            continue
                        if '=' not in line or line.startswith('#') or line.startswith('export'):
                            continue
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key, value = parts
                            if key.isidentifier() and not key.startswith('_') and '(' not in key:
                                env_vars[key] = value
                else:
                     self.logger.warning(f"Could not reliably find 'env' output after script execution: '{command_str}' in {cwd}")

            else:
                self.logger.warning(f"No stdout received from script execution and environment capture: '{command_str}' in {cwd}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Script execution failed during environment capture: {script_name} in {cwd}. Stderr: {e.stderr}")
            raise RuntimeError(f"Script {script_name} failed with exit code {e.returncode}") from e
        except FileNotFoundError as e:
            self.logger.error(f"Script or 'env' command not found during environment capture: {script_name} in {cwd}: {e}")
            raise RuntimeError(f"Required command not found for environment capture from script {script_name}") from e
        except Exception as e:
            self.logger.exception(f"Unexpected error capturing environment after executing {script_name} in {cwd}: {e}")
            raise RuntimeError(f"Unexpected error capturing environment after script {script_name}") from e

        if not env_vars:
            self.logger.error(f"Captured environment after executing {script_name} appears empty. This is unexpected.")
            # Avoid raising error here, allow build to potentially continue if env isn't strictly needed later
            # raise RuntimeError(f"Failed to capture environment after script {script_name} (result was empty).")

        self.logger.info(f"Successfully captured {len(env_vars)} environment variables after executing {script_name}")
        return env_vars


    def _execute_build_commands(self, commands: List[Dict[str, Any]], check: bool = True) -> None:
        for cmd_spec in commands:
            command_type = cmd_spec.pop("type", "shell_command") # Default to shell_command if not specified
            cwd = cmd_spec.get("cwd")
            if cwd:
                 # Expand user paths consistently
                 if isinstance(cwd, str):
                     cmd_spec["cwd"] = pathlib.Path(cwd).expanduser()
                 elif isinstance(cwd, pathlib.Path):
                     cmd_spec["cwd"] = cwd.expanduser() # Ensure Path objects are also expanded

            cmd_env = cmd_spec.get("env")
            if cmd_env is not None:
                 if not isinstance(cmd_env, dict):
                     self.logger.warning(f"Invalid 'env' type in cmd spec: {type(cmd_env)}. Ignoring.")
                     cmd_spec["env"] = None
                 else:
                      # Ensure all env vars are strings
                      cmd_spec["env"] = {str(k): str(v) for k, v in cmd_env.items()}


            # Default check to True unless explicitly set to False in spec
            cmd_check = cmd_spec.get("check", check)

            self.command_executor.execute(command_type, cmd_spec, check=cmd_check)


    def build_nebula_sdk(self) -> bool:
        build_type_name = "nebula-sdk"
        try:
            self.logger.info(f"Starting {build_type_name} build")
            commands: List[Dict[str, Any]] = [
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-sdk", "-o", str(self.nebula_sdk_output_path)], "cwd": self.grpower_path}
            ]
            self._execute_build_commands(commands)

            build_type_config = self.config.build_types.get(build_type_name)
            if build_type_config and build_type_config.post_build_git:
                self._handle_sdk_git_operations(build_type_name)

            self.logger.info(f"{build_type_name} build completed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError, Exception) as e:
            self.logger.error(f"{build_type_name} build failed: {e}", exc_info=True)
            return False

    def build_nebula(self) -> bool:
        build_type_name = "nebula"
        try:
            self.logger.info(f"Starting {build_type_name} build")

            self.logger.info("Capturing build environment from grpower env script...")
            nebula_build_env: Dict[str, str] = {}
            try:
                 nebula_build_env = self._get_environment_after_sourcing(
                      script_path=self.grpower_path / "scripts/env.sh",
                      cwd=self.grpower_path
                 )
                 if not nebula_build_env:
                     self.logger.warning("Captured build environment from grpower is empty. Proceeding cautiously.")
                     # Do not raise error, allow build to proceed
            except RuntimeError as e:
                  self.logger.error(f"Failed to capture grpower build environment: {e}. Proceeding without it.")
                  # Do not re-raise, allow build to proceed

            self.logger.info("Preparing initial build commands...")
            initial_commands_spec: List[Dict[str, Any]] = [
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["buildroot", "export_nebula_images", "-o", str(self.prebuilt_images_path)], "cwd": self.grpower_path}
            ]

            # Apply environment if captured
            commands_with_env = []
            if nebula_build_env:
                self.logger.info("Applying captured grpower environment to relevant commands...")
                target_scripts = ["gr-nebula.py", "gr-android.py"]
                for cmd_spec in initial_commands_spec:
                    current_command = cmd_spec.get("command")
                    # Check if command is one of the target scripts
                    is_target = False
                    if isinstance(current_command, str) and current_command in target_scripts:
                        is_target = True
                    elif isinstance(current_command, list) and current_command and current_command[0] in target_scripts:
                         is_target = True

                    if is_target:
                        modified_spec = cmd_spec.copy()
                        # Merge env: existing OS env + captured env
                        merged_env = os.environ.copy()
                        merged_env.update(nebula_build_env)
                        modified_spec["env"] = merged_env
                        modified_spec.pop("shell", None) # Let executor handle shell if needed based on command type
                        self.logger.debug(f"Injecting captured grpower env into command: {current_command}")
                        commands_with_env.append(modified_spec)
                    else:
                        commands_with_env.append(cmd_spec)
            else:
                 self.logger.warning("Skipping environment injection as grpower env capture failed or was empty.")
                 commands_with_env = initial_commands_spec

            self.logger.info("Executing initial build commands...")
            self._execute_build_commands(commands_with_env)

            src_elf = self.nebula_out_path / "build-zircon" / "build-venus-hee" / "zircon.elf"
            dst_elf = self.prebuilt_images_path / "nebula_kernel.elf"
            self.file_operator.copy_file(str(src_elf), str(dst_elf))

            self.logger.info("Configuring thyp-sdk environment by creating sdk_info link...")
            sdk_info_target = self.thyp_sdk_path / "sdk_info"
            nebula_sdk_source = self.nebula_sdk_output_path

            try:
                if not nebula_sdk_source.is_dir():
                     msg = f"Nebula SDK source directory does not exist: {nebula_sdk_source}"
                     self.logger.error(msg)
                     raise FileNotFoundError(msg)

                if sdk_info_target.is_symlink() or sdk_info_target.exists():
                    self.logger.debug(f"Removing existing sdk_info link/directory: {sdk_info_target}")
                    if sdk_info_target.is_symlink():
                        sdk_info_target.unlink()
                    elif sdk_info_target.is_dir():
                         shutil.rmtree(sdk_info_target)

                self.logger.info(f"Creating symlink: {sdk_info_target} -> {nebula_sdk_source}")
                os.symlink(nebula_sdk_source.resolve(), sdk_info_target, target_is_directory=True)
                self.logger.info("thyp-sdk environment configured successfully (sdk_info link created).")
            except OSError as e:
                self.logger.error(f"Failed to create symlink {sdk_info_target} -> {nebula_sdk_source}: {e}")
                raise
            except FileNotFoundError as e:
                 raise

            self.logger.info("Executing thyp-sdk configure script and capturing environment...")
            configure_script_path: pathlib.Path = self.thyp_sdk_path / 'configure.sh'
            configure_args: List[str] = [str(self.nebula_sdk_output_path.resolve())]
            configure_env: Dict[str, str] = {}
            try:
                configure_env = self._get_environment_after_script_execution(
                    script_path=configure_script_path,
                    script_args=configure_args,
                    cwd=self.thyp_sdk_path
                )
            except RuntimeError as e:
                self.logger.error(f"Failed to execute configure.sh or capture its environment: {e}. Proceeding without it.")
                # Allow build to continue without configure env

            self.logger.info("Successfully executed configure.sh.")
            if configure_env:
                 self.logger.info(f"Captured {len(configure_env)} variables from configure.sh.")
            else:
                 self.logger.warning("Environment capture after configure.sh failed or was empty.")


            self.logger.info("Preparing environment for build_all.sh...")
            build_all_env: Dict[str, str] = os.environ.copy() # Start with current OS env
            if configure_env:
                build_all_env.update(configure_env) # Overlay captured env

            # Ensure necessary locale settings
            build_all_env['LC_ALL'] = 'C.UTF-8'
            build_all_env['LANG'] = 'C.UTF-8'

            if 'PATH' not in build_all_env:
                self.logger.warning("PATH variable not found in environment for build_all.sh. Build might fail.")

            self.logger.debug(f"Environment prepared for build_all.sh with {len(build_all_env)} variables.")

            build_all_command_spec: List[Dict[str, Any]] = [
                 {
                     "command": "./build_all.sh", # Assume it's executable and in cwd
                     "cwd": self.thyp_sdk_path,
                     "shell": True, # Usually needed for scripts
                     "env": build_all_env
                 }
            ]
            self.logger.info("Executing thyp-sdk build script (build_all.sh) with prepared environment...")
            self._execute_build_commands(build_all_command_spec)

            self.logger.info("Performing post-build copy operations...")
            copy_success = self._perform_post_build_copy(build_type_name)
            if not copy_success:
                self.logger.error(f"Post-build copy step failed for {build_type_name}. Aborting build.")
                return False
            self.logger.info("Post-build copy operations completed successfully.")

            build_type_config = self.config.build_types.get(build_type_name)
            if build_type_config and build_type_config.post_build_git:
                self._handle_nebula_git_operations(build_type_name)

            self.logger.info(f"{build_type_name} build completed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError, RuntimeError, Exception) as e:
            self.logger.error(f"{build_type_name} build failed: {e}", exc_info=True)
            return False

    def build_tee(self) -> bool:
        build_type_name = "TEE"
        try:
            self.logger.info(f"Starting {build_type_name} build")

            build_type_config = self.config.build_types.get(build_type_name)
            if build_type_config and build_type_config.pre_build_clean:
                 self.clean_environment()

            commands: List[Dict[str, Any]] = [
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675_tee"], "cwd": self.grpower_path}
            ]
            self._execute_build_commands(commands)

            self.file_operator.create_directory(str(self.tee_temp_path))

            export_command: Dict[str, Any] = {
                 "command": "gr-android.py",
                 "args": ["buildroot", "export_nebula_images", "-o", str(self.tee_temp_path)],
                 "cwd": self.grpower_path
            }
            self.command_executor.execute("shell_command", export_command)


            self.file_operator.copy_wildcard(
                str(self.tee_temp_path / "nebula*.bin"),
                str(self.tee_kernel_path)
            )

            if build_type_config and build_type_config.post_build_git:
                self._handle_tee_git_operations(build_type_name)

            self.logger.info(f"{build_type_name} build completed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError, Exception) as e:
            self.logger.error(f"{build_type_name} build failed: {e}", exc_info=True)
            return False


    def _perform_post_build_copy(self, build_type_name: str) -> bool:
        self.logger.info(f"Starting post-build copy operations for {build_type_name}")
        build_type_config = self.config.build_types.get(build_type_name)

        if not build_type_config:
            self.logger.error(f"Build type config not found for '{build_type_name}' during post-build copy.")
            return False

        # Check if post_build_copy_operations exists and is not None
        copy_operations: Optional[List[FileCopyOperation]] = getattr(build_type_config, 'post_build_copy_operations', None)

        if not copy_operations:
            self.logger.info(f"No post-build copy operations defined or list is empty for {build_type_name}.")
            return True

        for op in copy_operations:
            try:
                # Resolve paths relative to their base directories
                source_base = self.thyp_sdk_path # Assuming most copies are from thyp_sdk
                dest_base = self.yocto_hypervisor_path # Assuming most copies are to yocto

                if op.is_wildcard:
                    absolute_source_pattern = str(source_base.joinpath(op.source_path))
                    absolute_destination_dir = str(dest_base.joinpath(op.destination_path))
                    self.logger.info(f"Copying wildcard: {absolute_source_pattern} -> {absolute_destination_dir}")
                    success = self.file_operator.copy_wildcard(absolute_source_pattern, absolute_destination_dir)
                else:
                    absolute_source_path = str(source_base.joinpath(op.source_path))
                    absolute_destination_path = str(dest_base.joinpath(op.destination_path))
                    self.logger.info(f"Copying file: {absolute_source_path} -> {absolute_destination_path}")
                    success = self.file_operator.copy_file(absolute_source_path, absolute_destination_path)

                if not success:
                    # Error logged by file_operator, just return False
                    return False

            except Exception as e:
                self.logger.exception(f"Unexpected error during post-build copy operation (source='{op.source_path}', dest='{op.destination_path}'): {e}")
                return False

        self.logger.info(f"Successfully completed all post-build copy operations for {build_type_name}.")
        return True

    def _get_git_config(self) -> Optional[BuildGitConfig]:
        # This method might still be needed for commit messages/author
        if not hasattr(self.config, 'git') or not isinstance(self.config.git, BuildGitConfig):
             self.logger.error("Build configuration missing 'git' section of type BuildGitConfig.")
             return None
        return self.config.git

    def _find_git_repo_info_by_path(self, target_path: str) -> Optional[GitRepoInfo]:
        """Finds the GitRepoInfo matching the normalized target path."""
        try:
            # Normalize the input path to handle relative paths, symlinks, etc.
            normalized_target_path = pathlib.Path(target_path).expanduser().resolve().as_posix()
            self.logger.debug(f"Normalized target path for lookup: {normalized_target_path}")

            for repo_info in self.all_repos_config.all_git_repos():
                if repo_info.repo_path:
                    normalized_repo_path = pathlib.Path(repo_info.repo_path).expanduser().resolve().as_posix()
                    # Added debug log as requested
                    self.logger.debug(f"Lookup Comparison: Target='{normalized_target_path}' vs Repo='{normalized_repo_path}' (RepoName: {repo_info.repo_name})")
                    if normalized_target_path == normalized_repo_path:
                        self.logger.info(f"Found matching GitRepoInfo for path {target_path}: {repo_info.repo_name}")
                        return repo_info
                else:
                    self.logger.debug(f"Skipping repo_info {repo_info.repo_name} due to missing repo_path")

            self.logger.warning(f"Could not find GitRepoInfo for path: {target_path} (normalized: {normalized_target_path})")
            return None
        except Exception as e:
            self.logger.exception(f"Error during GitRepoInfo lookup for path {target_path}: {e}")
            return None

    def _push_repo_changes(self, repo_info: GitRepoInfo) -> None:
        """Pushes changes using Gerrit refspec format based on GitRepoInfo."""
        repository_path = repo_info.repo_path
        remote_name = repo_info.remote_name
        target_branch = repo_info.remote_branch

        if not repository_path:
             self.logger.error(f"Skipping push for {repo_info.repo_name}: Repo path is missing.")
             return

        if not remote_name:
            self.logger.error(f"Skipping push for {repo_info.repo_name} ({repository_path}): Remote name is missing in its configuration.")
            return

        if not target_branch:
            self.logger.error(f"Skipping push for {repo_info.repo_name} ({repository_path}): Target remote branch is missing in its configuration.")
            return

        # Construct the Gerrit refspec
        remote_ref = f"HEAD:refs/for/{target_branch}"
        self.logger.info(f"Attempting Gerrit push for {repository_path} to {remote_name}/{target_branch} using refspec {remote_ref}")

        # Correctly form the refspec for Gerrit: HEAD:refs/for/target_branch
        gerrit_remote_ref = f"refs/for/{target_branch}"
        push_success = self.git_operator.push_to_remote(
            repository_path=repository_path,
            remote_name=remote_name,
            local_branch="HEAD",  # Push the current commit
            remote_branch=gerrit_remote_ref # Use the specific Gerrit target ref
        )

        if not push_success:
            self.logger.error(f"Gerrit push failed for {repository_path} to {remote_name} using refspec {remote_ref}.")
        else:
            self.logger.info(f"Gerrit push successful for {repository_path} to {remote_name} using refspec {remote_ref}.")


    def _perform_repo_git_operations(
        self,
        repo_path: str,
        paths_to_add: List[str],
        commit_message: str,
        commit_author: str,
        should_push: bool,
        repo_context_name: str # For logging purposes
    ) -> None:
        """Handles git add, commit, and optional push for a specific repo."""
        self.logger.info(f"Processing Git operations for {repo_context_name} repository: {repo_path}")
        repo_info = self._find_git_repo_info_by_path(repo_path)

        if not repo_info:
            self.logger.error(f"Could not find GitRepoInfo for {repo_context_name} repository path: {repo_path}. Skipping Git operations.")
            return

        add_success = self.git_operator.safe_add(repo_path, paths_to_add)
        # Assuming commit handles "nothing to commit" gracefully.
        # safe_add returns True even if nothing matched but command succeeded.

        commit_success = self.git_operator.commit_with_author(
            repo_path,
            commit_message,
            commit_author
        )

        if commit_success and should_push:
            self.logger.info(f"Attempting push for {repo_context_name} repository: {repo_path}")
            self._push_repo_changes(repo_info)
        elif not commit_success:
            self.logger.warning(f"Commit failed or nothing to commit for {repo_context_name} repository: {repo_path}. Skipping push.")
        else: # Commit successful but push disabled
            self.logger.info(f"Push disabled. Skipping push for {repo_context_name} repository: {repo_path}.")


    def _handle_sdk_git_operations(self, build_type_name: str) -> None:
        repo_path_to_push = str(self.nebula_sdk_output_path)
        git_config = self._get_git_config() # Still needed for commit message/author
        if not git_config: return

        add_paths = git_config.sdk_paths_to_add if git_config.sdk_paths_to_add else ["."]
        self.git_operator.safe_add(repo_path_to_push, add_paths)

        commit_success = self.git_operator.commit_with_author(
            repo_path_to_push,
            git_config.commit_message_sdk,
            git_config.commit_author
        )

        # Push only if commit was successful (or nothing to commit)
        if commit_success:
            build_type_config = self.config.build_types.get(build_type_name)
            if build_type_config and build_type_config.post_build_git:
                 self.logger.info(f"Post-build git push enabled for {build_type_name}. Attempting push...")
                 repo_info = self._find_git_repo_info_by_path(repo_path_to_push)
                 if repo_info:
                     self._push_repo_changes(repo_info)
                 else:
                      self.logger.error(f"Skipping push for {repo_path_to_push}: Could not find matching GitRepoInfo.")
            else:
                 self.logger.info(f"Post-build git push disabled for {build_type_name}, skipping push.")

    def _handle_nebula_git_operations(self, build_type_name: str) -> None:
        git_config = self._get_git_config()
        if not git_config:
            self.logger.error("Git configuration missing, cannot perform Git operations.")
            return

        build_type_config = self.config.build_types.get(build_type_name)
        should_push = build_type_config and build_type_config.post_build_git

        # Prebuilt Images Section (Context: /home/nebula/grt)
        self._perform_repo_git_operations(
            repo_path="/home/nebula/grt",
            paths_to_add=["thyp-sdk/products/mt8678-mix/prebuilt-images"],
            commit_message=git_config.commit_message_nebula,
            commit_author=git_config.commit_author,
            should_push=should_push,
            repo_context_name="GRT (prebuilt)"
        )

        # Yocto Sub-Repository Section (Context: /home/nebula/yocto/prebuilt/hypervisor/grt)
        self._perform_repo_git_operations(
            repo_path=str(self.yocto_hypervisor_path),
            paths_to_add=["."],
            commit_message=git_config.commit_message_nebula, # Assuming same message
            commit_author=git_config.commit_author,
            should_push=should_push,
            repo_context_name="Yocto sub-repo (hypervisor)"
        )


    def _handle_tee_git_operations(self, build_type_name: str) -> None:
        repo_path_to_push = str(self.tee_kernel_path)
        git_config = self._get_git_config() # Still needed for commit message/author
        if not git_config: return

        self.git_operator.safe_add(repo_path_to_push, ["."])
        commit_success = self.git_operator.commit_with_author(
            repo_path_to_push,
            git_config.commit_message_tee,
            git_config.commit_author
        )

        # Push only if commit was successful (or nothing to commit)
        if commit_success:
            build_type_config = self.config.build_types.get(build_type_name)
            if build_type_config and build_type_config.post_build_git:
                 self.logger.info(f"Post-build git push enabled for {build_type_name}. Attempting push...")
                 repo_info = self._find_git_repo_info_by_path(repo_path_to_push)
                 if repo_info:
                     self._push_repo_changes(repo_info)
                 else:
                      self.logger.error(f"Skipping push for {repo_path_to_push}: Could not find matching GitRepoInfo.")
            else:
                 self.logger.info(f"Post-build git push disabled for {build_type_name}, skipping push.")


    def build(self, build_types_requested: Optional[List[str]] = None) -> bool:
        enabled_build_types_in_config = {
            name for name, bt_conf in self.config.build_types.items() if bt_conf.enabled
        }

        if build_types_requested:
             # Validate requested types against config keys
             valid_requested = [bt for bt in build_types_requested if bt in self.config.build_types]
             invalid_requested = list(set(build_types_requested) - set(valid_requested))
             if invalid_requested:
                  self.logger.warning(f"Ignoring requested build types not found in config: {invalid_requested}")
             final_build_types = set(valid_requested)
        else:
             final_build_types = enabled_build_types_in_config

        if not final_build_types:
            self.logger.warning("No valid build types specified or enabled in config. Nothing to build.")
            return True # No failure if nothing was supposed to be built

        self.logger.info(f"Starting build process for types: {list(final_build_types)}")

        if self.config.enable_environment_cleanup:
            self.clean_environment()

        overall_success: bool = True
        # Define canonical build order
        build_order = ["nebula-sdk", "nebula", "TEE"]
        # Filter and order the types to build
        types_to_build_ordered = [bt for bt in build_order if bt in final_build_types]
        # Add any remaining types (not in the canonical order) at the end
        types_to_build_ordered.extend(list(final_build_types - set(build_order)))


        for build_type in types_to_build_ordered:
            # Config should exist based on earlier filtering, but double-check
            if build_type not in self.config.build_types:
                self.logger.error(f"Internal Error: Configuration for build type '{build_type}' unexpectedly missing, skipping.")
                overall_success = False
                continue


            build_config = self.config.build_types[build_type]
            # This check might be redundant now due to initial filtering, but harmless
            if not build_config.enabled and build_type not in (build_types_requested or []):
                 self.logger.info(f"Build type '{build_type}' is disabled and was not explicitly requested, skipping.")
                 continue


            self.logger.info(f"--- Starting build: {build_type} ---")
            build_method_name = f"build_{build_type.replace('-', '_')}"
            build_method = getattr(self, build_method_name, None)

            if callable(build_method):
                try:
                    # Pass build_type_name to the build method if needed, though current ones don't use it
                    success: bool = build_method() # Call the specific build method
                    overall_success &= success
                    self.logger.info(f"--- Finished build: {build_type} {'SUCCESS' if success else 'FAILED'} ---")
                except Exception as e:
                     # Log exception details for better debugging
                     self.logger.exception(f"Unexpected error during build method {build_method_name} for type {build_type}: {e}")
                     overall_success = False
                     self.logger.error(f"--- Finished build: {build_type} FAILED (Exception) ---")

            else:
                self.logger.error(f"Build method '{build_method_name}' for type '{build_type}' not found or not callable.")
                overall_success = False
                self.logger.error(f"--- Finished build: {build_type} FAILED (Not Found) ---")

        self.logger.info(f"Overall build process completed. Success: {overall_success}")
        return overall_success
