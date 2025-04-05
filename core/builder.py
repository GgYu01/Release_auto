from dataclasses import asdict
from typing import List, Dict, Optional
from config.schemas import BuildConfig, BuildTypeConfig
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from utils.file_utils import FileOperator
from utils.git_utils import GitOperator
import os
import pathlib

class BuildSystem:
    def __init__(self, build_config: BuildConfig, command_executor: CommandExecutor):
        self.config = build_config
        self.command_executor = command_executor
        self.logger = Logger(name=self.__class__.__name__)
        self.file_operator = FileOperator()
        self.git_operator = GitOperator(command_executor)

    def clean_environment(self):
        if not self.config.enable_environment_cleanup:
            self.logger.info("Environment cleanup disabled, skipping...")
            return

        paths_to_clean = [
            (self.config.paths.grpower_workspace, ["buildroot-pvt8675/", "nebula-ree/", "buildroot-pvt8675_tee/"]),
            (self.config.paths.nebula_out, [""])
        ]

        for base_path, subpaths in paths_to_clean:
            expanded_base = os.path.expanduser(base_path)
            for subpath in subpaths:
                full_path = os.path.join(expanded_base, subpath)
                self.logger.info(f"Cleaning path: {full_path}")
                self.file_operator.remove_directory_recursive(full_path)

    def build_nebula_sdk(self):
        try:
            self.logger.info("Starting nebula-sdk build")
            commands = [
                {"command": "export", "args": ["NO_PIPENV_SHELL=1"]},
                {"command": "cd", "args": ["~/grpower/"]},
                {"command": "source", "args": ["scripts/env.sh"]},
                {"command": "gr-nebula.py", "args": ["build"]},
                {"command": "gr-nebula.py", "args": ["export-buildroot"]},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"]},
                {"command": "gr-nebula.py", "args": ["export-sdk", "-o", self.config.paths.nebula_sdk_output]}
            ]

            for cmd in commands:
                self.command_executor.execute("shell_command", cmd)

            if self.config.build_types["nebula-sdk"].post_build_git:
                self._handle_sdk_git_operations()

            self.logger.info("nebula-sdk build completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"nebula-sdk build failed: {e}")
            return False

    def build_nebula(self):
        try:
            self.logger.info("Starting nebula build")
            commands = [
                {"command": "export", "args": ["NO_PIPENV_SHELL=1"]},
                {"command": "cd", "args": ["~/grpower/"]},
                {"command": "source", "args": ["scripts/env.sh"]},
                {"command": "gr-nebula.py", "args": ["build"]},
                {"command": "gr-nebula.py", "args": ["export-buildroot"]},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675"]},
                {"command": "gr-android.py", "args": ["buildroot", "export_nebula_images", "-o", self.config.paths.prebuilt_images]}
            ]

            for cmd in commands:
                self.command_executor.execute("shell_command", cmd)

            # Copy zircon.elf
            src_elf = os.path.join(self.config.paths.nebula_out, "build-zircon/build-venus-hee/zircon.elf")
            dst_elf = os.path.join(self.config.paths.prebuilt_images, "nebula_kernel.elf")
            self.file_operator.copy_file(src_elf, dst_elf)

            # Configure and build thyp-sdk
            self.command_executor.execute("shell_command", {
                "command": "./configure.sh",
                "args": [self.config.paths.nebula_sdk_output, ">", "/dev/null"],
                "cwd": self.config.paths.thyp_sdk_path
            })

            self.command_executor.execute("shell_command", {
                "command": "./build_all.sh",
                "cwd": self.config.paths.thyp_sdk_path
            })

            if self.config.build_types["nebula"].post_build_git:
                self._handle_nebula_git_operations()

            self.logger.info("nebula build completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"nebula build failed: {e}")
            return False

    def build_tee(self):
        try:
            self.logger.info("Starting TEE build")
            
            # Clean environment first
            if self.config.build_types["TEE"].pre_build_clean:
                self.clean_environment()

            commands = [
                {"command": "export", "args": ["NO_PIPENV_SHELL=1"]},
                {"command": "cd", "args": ["~/grpower/"]},
                {"command": "source", "args": ["scripts/env.sh"]},
                {"command": "gr-nebula.py", "args": ["build"]},
                {"command": "gr-nebula.py", "args": ["export-buildroot"]},
                {"command": "gr-android.py", "args": ["set-product", "--product-name", "pvt8675_tee"]}
            ]

            for cmd in commands:
                self.command_executor.execute("shell_command", cmd)

            # Create temp directory and export images
            self.file_operator.create_directory(self.config.paths.tee_temp)
            
            self.command_executor.execute("shell_command", {
                "command": "gr-android.py",
                "args": ["buildroot", "export_nebula_images", "-o", self.config.paths.tee_temp]
            })

            # Copy TEE binaries
            self.file_operator.copy_wildcard(
                os.path.join(self.config.paths.tee_temp, "nebula*.bin"),
                self.config.paths.tee_kernel
            )

            if self.config.build_types["TEE"].post_build_git:
                self._handle_tee_git_operations()

            self.logger.info("TEE build completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"TEE build failed: {e}")
            return False

    def _handle_sdk_git_operations(self):
        self.git_operator.safe_add(
            self.config.paths.nebula_sdk_output,
            self.config.git.sdk_paths_to_add
        )
        self.git_operator.commit_with_author(
            self.config.paths.nebula_sdk_output,
            self.config.git.commit_message_sdk,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            self.config.paths.nebula_sdk_output,
            self.config.git.remote_name,
            "HEAD",
            self.config.git.remote_branch_nebula
        )

    def _handle_nebula_git_operations(self):
        # Git operations for thyp-sdk prebuilt images
        self.git_operator.safe_add(
            self.config.paths.prebuilt_images,
            ["."]
        )
        self.git_operator.commit_with_author(
            self.config.paths.prebuilt_images,
            self.config.git.commit_message_nebula,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            self.config.paths.prebuilt_images,
            self.config.git.remote_name,
            "HEAD",
            self.config.git.remote_branch_nebula
        )

        # Git operations for yocto hypervisor
        self.git_operator.safe_add(
            self.config.paths.yocto_hypervisor,
            ["."]
        )
        self.git_operator.commit_with_author(
            self.config.paths.yocto_hypervisor,
            self.config.git.commit_message_nebula,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            self.config.paths.yocto_hypervisor,
            self.config.git.remote_name,
            "HEAD",
            self.config.git.remote_branch_nebula
        )

    def _handle_tee_git_operations(self):
        kernel_path = os.path.join(self.config.paths.tee_kernel)
        self.git_operator.safe_add(
            kernel_path,
            ["."]
        )
        self.git_operator.commit_with_author(
            kernel_path,
            self.config.git.commit_message_tee,
            self.config.git.commit_author
        )
        self.git_operator.push_to_remote(
            kernel_path,
            self.config.git.remote_name,
            "HEAD",
            self.config.git.remote_branch_tee
        )

    def build(self, build_types: Optional[List[str]] = None):
        if not build_types:
            build_types = [bt.name for bt in self.config.build_types.values() if bt.enabled]

        if not build_types:
            self.logger.warning("No build types specified or enabled")
            return False

        self.logger.info(f"Starting build process for types: {build_types}")

        if self.config.enable_environment_cleanup:
            self.clean_environment()

        success = True
        for build_type in build_types:
            if build_type not in self.config.build_types:
                self.logger.error(f"Unknown build type: {build_type}")
                continue

            build_config = self.config.build_types[build_type]
            if not build_config.enabled and build_type in build_types:
                build_config.enabled = True

            if build_type == "nebula-sdk":
                success &= self.build_nebula_sdk()
            elif build_type == "nebula":
                success &= self.build_nebula()
            elif build_type == "TEE":
                success &= self.build_tee()

        return success
