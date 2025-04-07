import os
import pathlib
import shlex
import shutil
import subprocess
from dataclasses import asdict
from typing import List, Dict, Optional, Any, Tuple
from config.schemas import BuildConfig, BuildTypeConfig
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from utils.file_utils import FileOperator
from utils.git_utils import GitOperator


class BuildSystem:
    def __init__(self, build_config: BuildConfig, command_executor: CommandExecutor) -> None:
        self.config: BuildConfig = build_config
        self.command_executor: CommandExecutor = command_executor
        self.logger: Logger = Logger(name=self.__class__.__name__)
        self.file_operator: FileOperator = FileOperator()
        self.git_operator: GitOperator = GitOperator(command_executor)

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
        # Use the script name, cwd handles the directory context
        command_str = f"export NO_PIPENV_SHELL=1 && source {shlex.quote(str(script_path))} && env"
        self.logger.debug(f"Attempting to capture environment using command in {cwd}: {command_str}")
        try:
            # Need capture_output=True and text=True for this specific call.
            # Call _run_subprocess directly from the executor instance.
            # Note: command_executor instance is self.command_executor
            process_result = self.command_executor._run_subprocess(
                 command=command_str,
                 cwd=cwd,
                 shell=True,         # Crucial for sourcing
                 capture_output=True,# Need to capture
                 text=True,          # Need text output
                 check=True          # Raise on non-zero exit
             )

            if process_result.stdout:
                for line in process_result.stdout.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    # Basic check to avoid lines that are clearly not variable assignments
                    if '=' not in line or line.startswith('#') or line.startswith('export'):
                        continue
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        # Further filter potentially problematic entries like functions
                        if key.isidentifier() and not key.startswith('_') and '(' not in key:
                           env_vars[key] = value
                           # self.logger.debug(f"Captured env var: {key}") # Optional: too verbose?
                        # else:
                        #    self.logger.debug(f"Skipping potential non-variable env line: '{line}'")
                    # else: # This case should be rare now due to '=' check above
                        # self.logger.warning(f"Could not parse environment line: '{line}' from script {script_path.name}")
            else:
                 self.logger.warning(f"No stdout received from environment capture command: '{command_str}' in {cwd}")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Failed to execute or find command for environment capture from {script_path.name} in {cwd}: {e}")
            # Propagate the error to stop the build process
            raise RuntimeError(f"Failed to capture environment from script {script_path.name}") from e
        except Exception as e:
             self.logger.exception(f"Unexpected error capturing environment from {script_path.name} in {cwd}: {e}")
             # Propagate the error
             raise RuntimeError(f"Unexpected error capturing environment from script {script_path.name}") from e

        if not env_vars:
             # Log as warning, but let the caller decide if it's fatal
             self.logger.warning(f"Captured environment from {script_path.name} appears empty.")

        self.logger.info(f"Successfully captured {len(env_vars)} environment variables from {script_path.name}")
        return env_vars

    def _execute_build_commands(self, commands: List[Dict[str, Any]], check: bool = True) -> None:
        for cmd_spec in commands:
            command_type = cmd_spec.pop("type", "shell_command")
            # Ensure cwd is Path object if present
            cwd = cmd_spec.get("cwd")
            if cwd:
                 if isinstance(cwd, str):
                     cmd_spec["cwd"] = pathlib.Path(cwd).expanduser()
                 elif isinstance(cwd, pathlib.Path):
                     cmd_spec["cwd"] = cwd.expanduser() # Ensure expanded

            cmd_env = cmd_spec.get("env")
            if cmd_env is not None and not isinstance(cmd_env, dict):
                 self.logger.warning(f"Invalid 'env' type in cmd spec: {type(cmd_env)}. Ignoring.")
                 cmd_spec["env"] = None

            self.command_executor.execute(command_type, cmd_spec, check=check)


    def build_nebula_sdk(self) -> bool:
        try:
            self.logger.info("Starting nebula-sdk build")
            # Removed source_command. Env vars must be passed explicitly if needed.
            commands: List[Dict[str, Any]] = [
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-sdk", "-o", str(self.nebula_sdk_output_path)], "cwd": self.grpower_path}
            ]
            self._execute_build_commands(commands)

            if self.config.build_types["nebula-sdk"].post_build_git:
                self._handle_sdk_git_operations()

            self.logger.info("nebula-sdk build completed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            self.logger.error(f"nebula-sdk build failed: {e}")
            return False

    def build_nebula(self) -> bool:
        try:
            self.logger.info("Starting nebula build")
            # Capture environment from grpower env script
            self.logger.info("Capturing build environment from grpower env script...")
            nebula_build_env: Dict[str, str] = {}
            try:
                 nebula_build_env = self._get_environment_after_sourcing(
                      script_path=self.grpower_path / "scripts/env.sh",
                      cwd=self.grpower_path
                 )
                 if not nebula_build_env:
                      # Helper method logged the warning, but we treat empty env as fatal here
                      self.logger.error("Captured build environment is empty. Cannot proceed.")
                      raise RuntimeError("Failed to capture necessary build environment from grpower (empty result).")
            except RuntimeError as e:
                  self.logger.error(f"Failed to capture build environment: {e}")
                  # Re-raise to be caught by the main try-except block below
                  raise

            self.logger.info("Preparing initial build commands with captured environment...")
            initial_commands_spec: List[Dict[str, Any]] = [
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["buildroot", "export_nebula_images", "-o", str(self.prebuilt_images_path)], "cwd": self.grpower_path}
            ]

            # Inject the captured environment only into the specific script calls
            commands_with_env: List[Dict[str, Any]] = []
            target_scripts = ["gr-nebula.py", "gr-android.py"]
            for cmd_spec in initial_commands_spec:
                current_command = cmd_spec.get("command")
                # Ensure command is a string for comparison
                if isinstance(current_command, str) and current_command in target_scripts:
                    modified_spec = cmd_spec.copy()
                    modified_spec["env"] = nebula_build_env
                    # Ensure shell=False (it's the default for _run_subprocess when command is list/string+args)
                    modified_spec.pop("shell", None) # Remove shell if it somehow got added
                    self.logger.debug(f"Injecting captured env into command: {current_command}")
                    commands_with_env.append(modified_spec)
                elif isinstance(current_command, list) and current_command and current_command[0] in target_scripts:
                     # Handle case where command might be a list like ["python", "script.py"]
                     modified_spec = cmd_spec.copy()
                     modified_spec["env"] = nebula_build_env
                     modified_spec.pop("shell", None)
                     self.logger.debug(f"Injecting captured env into command list: {current_command}")
                     commands_with_env.append(modified_spec)
                else:
                    commands_with_env.append(cmd_spec) # Append unmodified spec

            self.logger.info("Executing initial build commands...")
            self._execute_build_commands(commands_with_env) # Use the modified list

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
                os.symlink(nebula_sdk_source, sdk_info_target, target_is_directory=True)
                self.logger.info("thyp-sdk environment configured successfully (sdk_info link created).")
            except OSError as e:
                self.logger.error(f"Failed to create symlink {sdk_info_target} -> {nebula_sdk_source}: {e}")
                raise
            except FileNotFoundError as e:
                 # Already logged specific error
                 raise


            thyp_sdk_path_str = str(self.thyp_sdk_path.resolve())
            build_env = os.environ.copy()
            build_env['SDK_APP_DIR'] = thyp_sdk_path_str

            sdk_local_bin = os.path.join(thyp_sdk_path_str, '.local', 'bin')
            sdk_host_tools = os.path.join(
                thyp_sdk_path_str, 'scripts', 'host-tools'
            )
            original_path = build_env.get('PATH', '')
            build_env['PATH'] = os.pathsep.join(
                [sdk_local_bin, sdk_host_tools, original_path]
            )

            build_env['LC_ALL'] = 'C.UTF-8'
            build_env['LANG'] = 'C.UTF-8'
            self.logger.info(
                "Executing thyp-sdk configure script (configure.sh)..."
            )
            configure_command: List[Dict[str, Any]] = [
                 {
                     "command": [
                         "./configure.sh",
                         str(self.nebula_sdk_output_path.resolve())
                     ],
                     "cwd": self.thyp_sdk_path,
                     "shell": True,
                     "env": build_env
                 }
            ]
            self._execute_build_commands(configure_command)

            build_all_command: List[Dict[str, Any]] = [
                 {
                     "command": "./build_all.sh",
                     "cwd": self.thyp_sdk_path,
                     "shell": True,
                     "env": build_env
                 }
            ]
            self.logger.info("Executing thyp-sdk build script (build_all.sh)...")
            self._execute_build_commands(build_all_command)

            if self.config.build_types["nebula"].post_build_git:
                self._handle_nebula_git_operations()

            self.logger.info("nebula build completed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError, Exception) as e:
            self.logger.error(f"nebula build failed: {e}")
            return False

    def build_tee(self) -> bool:
        try:
            self.logger.info("Starting TEE build")

            if self.config.build_types["TEE"].pre_build_clean:
                 self.clean_environment()

            # Removed source_command
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

            if self.config.build_types["TEE"].post_build_git:
                self._handle_tee_git_operations()

            self.logger.info("TEE build completed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            self.logger.error(f"TEE build failed: {e}")
            return False

    def _handle_sdk_git_operations(self) -> None:
        repo_path = str(self.nebula_sdk_output_path)
        self.git_operator.safe_add(
            repo_path,
            self.config.git.sdk_paths_to_add
        )
        self.git_operator.commit_with_author(
            repo_path,
            self.config.git.commit_message_sdk,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            repo_path,
            self.config.git.remote_name,
            "HEAD",
            self.config.git.remote_branch_nebula
        )

    def _handle_nebula_git_operations(self) -> None:
        repo_path_prebuilt = str(self.prebuilt_images_path)
        self.git_operator.safe_add(repo_path_prebuilt, ["."])
        self.git_operator.commit_with_author(
            repo_path_prebuilt,
            self.config.git.commit_message_nebula,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            repo_path_prebuilt,
            self.config.git.remote_name, "HEAD",
            self.config.git.remote_branch_nebula
        )

        repo_path_yocto = str(self.yocto_hypervisor_path)
        self.git_operator.safe_add(repo_path_yocto, ["."])
        self.git_operator.commit_with_author(
            repo_path_yocto,
            self.config.git.commit_message_nebula,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            repo_path_yocto,
            self.config.git.remote_name, "HEAD",
            self.config.git.remote_branch_nebula
        )

    def _handle_tee_git_operations(self) -> None:
        repo_path = str(self.tee_kernel_path)
        self.git_operator.safe_add(repo_path, ["."])
        self.git_operator.commit_with_author(
            repo_path,
            self.config.git.commit_message_tee,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            repo_path,
            self.config.git.remote_name, "HEAD",
            self.config.git.remote_branch_tee
        )

    def build(self, build_types_requested: Optional[List[str]] = None) -> bool:
        enabled_build_types_in_config = {
            name for name, bt_conf in self.config.build_types.items() if bt_conf.enabled
        }

        if build_types_requested:
             final_build_types = set(build_types_requested)
        else:
             final_build_types = enabled_build_types_in_config

        if not final_build_types:
            self.logger.warning("No build types specified or enabled in config.")
            return False

        self.logger.info(f"Starting build process for types: {list(final_build_types)}")

        if self.config.enable_environment_cleanup:
            self.clean_environment()

        overall_success: bool = True
        build_order = ["nebula-sdk", "nebula", "TEE"]
        types_to_build_ordered = [bt for bt in build_order if bt in final_build_types]
        types_to_build_ordered.extend(list(final_build_types - set(build_order)))


        for build_type in types_to_build_ordered:
            if build_type not in self.config.build_types:
                self.logger.error(f"Configuration for build type '{build_type}' not found, skipping.")
                overall_success = False
                continue


            build_config = self.config.build_types[build_type]
            if not build_config.enabled and build_type not in (build_types_requested or []):
                 self.logger.info(f"Build type '{build_type}' is disabled and not requested, skipping.")
                 continue


            self.logger.info(f"--- Starting build: {build_type} ---")
            build_method_name = f"build_{build_type.replace('-', '_')}"
            build_method = getattr(self, build_method_name, None)

            if callable(build_method):
                try:
                    success: bool = build_method()
                    overall_success &= success
                    self.logger.info(f"--- Finished build: {build_type} {'SUCCESS' if success else 'FAILED'} ---")
                except Exception as e:
                     self.logger.exception(f"Unexpected error during build method {build_method_name}: {e}")
                     overall_success = False
                     self.logger.error(f"--- Finished build: {build_type} FAILED (Exception) ---")

            else:
                self.logger.error(f"Build method '{build_method_name}' for type '{build_type}' not found.")
                overall_success = False
                self.logger.error(f"--- Finished build: {build_type} FAILED (Not Found) ---")

        self.logger.info(f"Overall build process completed. Success: {overall_success}")
        return overall_success
