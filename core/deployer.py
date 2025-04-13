import os
import shlex
import subprocess
from config.schemas import DeployConfig
from utils.custom_logger import Logger
from utils.command_executor import CommandExecutor


class Deployer:
    def __init__(self, command_executor: CommandExecutor, logger: Logger):
        if not command_executor:
            raise ValueError("CommandExecutor instance is required")
        if not logger:
            raise ValueError("Logger instance is required")
        self.command_executor = command_executor
        self.logger = logger

    def deploy_package(self, local_zip_path: str, deploy_config: DeployConfig) -> bool:
        """
        Deploys the release package (ZIP file) to the remote server via SCP.

        Args:
            local_zip_path: The absolute path to the local ZIP file to deploy.
            deploy_config: Configuration object with SCP details.

        Returns:
            True if deployment was successful, False otherwise.
        """
        self.logger.info("Starting deployment process...")

        if not os.path.isfile(local_zip_path):
            self.logger.error(f"Deployment failed: Local package file not found at {local_zip_path}")
            return False

        # Basic validation of config
        if not all([deploy_config.scp_host, deploy_config.scp_user, deploy_config.scp_remote_path]):
             self.logger.error("Deployment failed: SCP configuration (host, user, remote_path) is incomplete.")
             return False

        # Construct the remote target path
        # Ensure remote path uses forward slashes, even if config uses backslashes
        remote_path_normalized = deploy_config.scp_remote_path.replace('\\', '/')
        # Ensure trailing slash if it's meant to be a directory
        if not remote_path_normalized.endswith('/'):
            remote_path_normalized += '/'
        remote_target = f"{deploy_config.scp_user}@{deploy_config.scp_host}:{remote_path_normalized}"

        # Construct the SCP command arguments carefully
        scp_command = "scp"
        # Use '-o StrictHostKeyChecking=no' and '-o UserKnownHostsFile=/dev/null' for automation,
        # but be aware of the security implications (MITM). Relying on pre-configured keys is better.
        # For now, assume keys are set up and omit these.
        scp_args = [
            "-P", str(deploy_config.scp_port),  # Port option
            local_zip_path,                    # Source file
            remote_target                      # Destination
        ]

        # Log a representation without potentially sensitive info if needed
        self.logger.info(f"Preparing SCP command to transfer {os.path.basename(local_zip_path)} to {deploy_config.scp_host}:{remote_path_normalized}")
        # More detailed log for debugging:
        self.logger.debug(f"Executing SCP command: {scp_command} {' '.join(scp_args)}")

        try:
            # Adapt this call based on the actual CommandExecutor interface
            # Option 1: Assuming execute takes a command name and params dict with list
            params = {
                "command_list": [scp_command] + scp_args
            }
            result = self.command_executor.execute("scp_transfer", params)

            # Option 2: Assuming execute_shell_command exists and takes a string
            # command_string = f"{scp_command} {' '.join(scp_args)}"
            # result = self.command_executor.execute_shell_command(command_string, shell=True) # If shell=True needed

            # Check result based on CommandExecutor's return type (e.g., CompletedProcess)
            if hasattr(result, 'returncode') and result.returncode != 0:
                 # CommandExecutor might handle this and raise CalledProcessError instead
                 self.logger.error(f"SCP deployment failed. Command returned non-zero exit code: {result.returncode}")
                 self.logger.error(f"SCP stderr: {getattr(result, 'stderr', 'N/A')}")
                 self.logger.error(f"SCP stdout: {getattr(result, 'stdout', 'N/A')}")
                 return False

            self.logger.info("SCP command executed successfully.")
            self.logger.debug(f"SCP stdout: {getattr(result, 'stdout', 'N/A')}")
            self.logger.debug(f"SCP stderr: {getattr(result, 'stderr', 'N/A')}")
            self.logger.info(f"Successfully deployed {os.path.basename(local_zip_path)} to {deploy_config.scp_host}:{remote_path_normalized}")
            return True

        except subprocess.CalledProcessError as e: # If CommandExecutor raises this
            self.logger.error(f"SCP deployment failed. Return code: {e.returncode}")
            self.logger.error(f"SCP stderr: {getattr(e, 'stderr', 'N/A')}")
            self.logger.error(f"SCP stdout: {getattr(e, 'stdout', 'N/A')}")
            return False
        except ValueError as e: # Catch config errors from CommandExecutor setup
             self.logger.error(f"Configuration error during SCP execution setup: {e}")
             return False
        except FileNotFoundError: # If scp command itself is not found by the executor
             self.logger.error(f"SCP command '{scp_command}' not found. Ensure SCP client is installed and in PATH.")
             return False
        except Exception as e: # Catch other potential errors from CommandExecutor or SCP
            self.logger.error(f"An unexpected error occurred during deployment: {e}", exc_info=True)
            return False