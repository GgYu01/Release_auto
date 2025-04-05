import os
import pathlib
from dataclasses import asdict
from typing import List, Dict, Optional, Any
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
        # Define common paths early
        self.grpower_path: str = os.path.expanduser("~/grpower/")
        self.thyp_sdk_path: str = os.path.expanduser(self.config.paths.thyp_sdk_path)
        self.nebula_sdk_output_path: str = os.path.expanduser(self.config.paths.nebula_sdk_output)
        self.prebuilt_images_path: str = os.path.expanduser(self.config.paths.prebuilt_images)
        self.nebula_out_path: str = os.path.expanduser(self.config.paths.nebula_out)
        self.tee_temp_path: str = os.path.expanduser(self.config.paths.tee_temp)
        self.tee_kernel_path: str = os.path.expanduser(self.config.paths.tee_kernel)
        self.yocto_hypervisor_path: str = os.path.expanduser(self.config.paths.yocto_hypervisor)


    def clean_environment(self) -> None:
        if not self.config.enable_environment_cleanup:
            self.logger.info("Environment cleanup disabled, skipping...")
            return

        paths_to_clean = [
            (self.config.paths.grpower_workspace, ["buildroot-pvt8675/", "nebula-ree/", "buildroot-pvt8675_tee/"]),
            (self.nebula_out_path, [""]) # Use expanded path
        ]

        for base_path, subpaths in paths_to_clean:
            expanded_base = os.path.expanduser(base_path) # Keep expansion here for flexibility
            for subpath in subpaths:
                full_path = os.path.join(expanded_base, subpath)
                self.logger.info(f"Cleaning path: {full_path}")
                self.file_operator.remove_directory_recursive(full_path)

    def _execute_build_commands(self, commands: List[Dict[str, Any]]) -> None:
        for cmd_spec in commands:
            command_type = cmd_spec.pop("type", "shell_command") # Default to shell
            # Ensure cwd is expanded if present
            if "cwd" in cmd_spec and isinstance(cmd_spec["cwd"], str):
                cmd_spec["cwd"] = os.path.expanduser(cmd_spec["cwd"])
            self.command_executor.execute(command_type, cmd_spec)


    def build_nebula_sdk(self) -> bool:
        try:
            self.logger.info("Starting nebula-sdk build")
            commands: List[Dict[str, Any]] = [
                {"type": "source_command", "args": ["scripts/env.sh"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-sdk", "-o", self.nebula_sdk_output_path], "cwd": self.grpower_path}
            ]
            self._execute_build_commands(commands)

            if self.config.build_types["nebula-sdk"].post_build_git:
                self._handle_sdk_git_operations()

            self.logger.info("nebula-sdk build completed successfully")
            return True
        except Exception as e:
            # Log exception relies on CommandExecutor logging details
            self.logger.error(f"nebula-sdk build failed.")
            return False

    def build_nebula(self) -> bool:
        try:
            self.logger.info("Starting nebula build")
            commands: List[Dict[str, Any]] = [
                {"type": "source_command", "args": ["scripts/env.sh"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["buildroot", "export_nebula_images", "-o", self.prebuilt_images_path], "cwd": self.grpower_path}
            ]
            self._execute_build_commands(commands)

            # Copy zircon.elf
            src_elf = os.path.join(self.nebula_out_path, "build-zircon/build-venus-hee/zircon.elf")
            dst_elf = os.path.join(self.prebuilt_images_path, "nebula_kernel.elf")
            self.file_operator.copy_file(src_elf, dst_elf)

            # Configure and build thyp-sdk - Note: Redirection needs shell=True
            thyp_sdk_commands: List[Dict[str, Any]] = [
                 {"command": f"./configure.sh {shlex.quote(self.nebula_sdk_output_path)} > /dev/null", "cwd": self.thyp_sdk_path, "shell": True},
                 {"command": "./build_all.sh", "cwd": self.thyp_sdk_path, "shell": False} # Assuming build_all.sh doesn't need shell features
            ]
            self._execute_build_commands(thyp_sdk_commands)


            if self.config.build_types["nebula"].post_build_git:
                self._handle_nebula_git_operations()

            self.logger.info("nebula build completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"nebula build failed.")
            return False

    def build_tee(self) -> bool:
        try:
            self.logger.info("Starting TEE build")

            if self.config.build_types["TEE"].pre_build_clean:
                 # Ensure clean_environment uses expanded paths correctly if needed
                 # Current implementation seems okay, relies on FileOperator
                 self.clean_environment()

            commands: List[Dict[str, Any]] = [
                {"type": "source_command", "args": ["scripts/env.sh"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["build"], "cwd": self.grpower_path},
                {"command": "gr-nebula.py", "args": ["export-buildroot"], "cwd": self.grpower_path},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675_tee"], "cwd": self.grpower_path}
            ]
            self._execute_build_commands(commands)

            # Create temp directory and export images
            self.file_operator.create_directory(self.tee_temp_path)

            export_command: Dict[str, Any] = {
                 "command": "gr-android.py",
                 "args": ["buildroot", "export_nebula_images", "-o", self.tee_temp_path],
                 "cwd": self.grpower_path # Assume gr-android needs grpower context
            }
            self.command_executor.execute("shell_command", export_command)


            # Copy TEE binaries
            self.file_operator.copy_wildcard(
                os.path.join(self.tee_temp_path, "nebula*.bin"),
                self.tee_kernel_path # Destination directory
            )

            if self.config.build_types["TEE"].post_build_git:
                self._handle_tee_git_operations()

            self.logger.info("TEE build completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"TEE build failed.")
            return False

    def _handle_sdk_git_operations(self) -> None:
        repo_path = self.nebula_sdk_output_path
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
            "HEAD", # Assuming push current branch head
            self.config.git.remote_branch_nebula # Check if correct branch
        )

    def _handle_nebula_git_operations(self) -> None:
        # Git operations for thyp-sdk prebuilt images
        repo_path_prebuilt = self.prebuilt_images_path
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

        # Git operations for yocto hypervisor
        repo_path_yocto = self.yocto_hypervisor_path
        self.git_operator.safe_add(repo_path_yocto, ["."])
        self.git_operator.commit_with_author(
            repo_path_yocto,
            self.config.git.commit_message_nebula, # Same message used? Verify
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            repo_path_yocto,
            self.config.git.remote_name, "HEAD",
            self.config.git.remote_branch_nebula
        )

    def _handle_tee_git_operations(self) -> None:
        repo_path = self.tee_kernel_path # Path contains the files
        self.git_operator.safe_add(repo_path, ["."]) # Add files within the dir
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
        # Determine which build types are enabled in config or explicitly requested
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

        # Optional global cleanup before any builds start
        if self.config.enable_environment_cleanup:
            self.clean_environment() # Handles its own logging

        overall_success: bool = True
        # Process builds in a reasonable order if possible, or as requested
        # Define a potential order if needed, otherwise use set order
        build_order = ["nebula-sdk", "nebula", "TEE"] # Example order
        types_to_build_ordered = [bt for bt in build_order if bt in final_build_types]
        # Add any requested types not in the predefined order
        types_to_build_ordered.extend(list(final_build_types - set(build_order)))


        for build_type in types_to_build_ordered:
            if build_type not in self.config.build_types:
                self.logger.error(f"Configuration for build type '{build_type}' not found, skipping.")
                overall_success = False
                continue

            # Check if build type is enabled (either by config or request)
            # This logic might be redundant if final_build_types is derived correctly
            build_config = self.config.build_types[build_type]
            if not build_config.enabled and build_type not in (build_types_requested or []):
                 self.logger.info(f"Build type '{build_type}' is disabled and not requested, skipping.")
                 continue # Skip if disabled and not explicitly requested


            self.logger.info(f"--- Starting build: {build_type} ---")
            build_method = getattr(self, f"build_{build_type.replace('-', '_')}", None)

            if callable(build_method):
                success: bool = build_method()
                overall_success &= success
                self.logger.info(f"--- Finished build: {build_type} {'SUCCESS' if success else 'FAILED'} ---")
            else:
                self.logger.error(f"Build method for type '{build_type}' not found.")
                overall_success = False

        self.logger.info(f"Overall build process completed. Success: {overall_success}")
        return overall_success

import shlex # Ensure shlex is imported
