import os
import shlex
import subprocess
from logging import Logger # Correct import for Logger type hint

from config.schemas import DeployConfig
from utils.command_executor import CommandExecutor # Assuming CommandExecutor handles execution
from utils.custom_logger import Logger as CustomLogger # Keep if needed elsewhere

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
        Deploys the packaged release archive using SCP.

        Args:
            local_zip_path: The path to the local ZIP file to deploy.
            deploy_config: Configuration containing SCP connection details.

        Returns:
            True if deployment was successful, False otherwise.
        """
        self.logger.info(f"Starting deployment of {local_zip_path}...")

        # --- Input Validation ---
        if not os.path.exists(local_zip_path):
            self.logger.error(f"Deployment failed: Local package not found at {local_zip_path}")
            return False
        if not os.path.isfile(local_zip_path):
             self.logger.error(f"Deployment failed: Path {local_zip_path} is not a file.")
             return False

        if not all([deploy_config.scp_host, deploy_config.scp_user, deploy_config.scp_remote_path]):
            self.logger.error("Deployment failed: SCP configuration is incomplete (host, user, or remote_path missing).")
            return False

        # Ensure remote path uses forward slashes and handles potential directory targets
        remote_path = deploy_config.scp_remote_path.replace('\\', '/')
        # If it doesn't look like a specific filename, assume it's a directory and append a slash if missing
        # Note: This heuristic might not cover all cases, but is a common pattern.
        if not os.path.basename(remote_path) or '.' not in os.path.basename(remote_path):
             if not remote_path.endswith('/'):
                 remote_path += '/'
        # Alternatively, could append the local filename explicitly:
        # remote_target = f"{remote_path.rstrip('/')}/{os.path.basename(local_zip_path)}"

        # --- Construct SCP Command ---
        # Use shlex.quote for safety, or pass as a list to CommandExecutor if it supports it
        scp_command_parts = [
            "scp",
            "-P", str(deploy_config.scp_port), # Port must be string
            local_zip_path, # Already validated path
            f"{deploy_config.scp_user}@{deploy_config.scp_host}:{remote_path}"
        ]

        # Safer to pass as list if CommandExecutor supports it:
        # command_args = scp_command_parts
        # command_string = None # Let executor handle joining/quoting if necessary

        # If CommandExecutor expects a single string:
        command_string = " ".join(shlex.quote(part) for part in scp_command_parts)
        command_args = None

        self.logger.info(f"Executing SCP command: {' '.join(scp_command_parts)}") # Log unquoted for readability

        # --- Execute SCP Command ---
        try:
            # Choose the appropriate execution method based on CommandExecutor capabilities
            if command_args:
                 # Ideal: Pass list of arguments directly
                 result = self.command_executor.execute(command_args, command_type='list_command') # Hypothetical type
            elif command_string:
                 # Fallback: Pass quoted string
                 result = self.command_executor.execute(command_string, command_type='shell_command') # Assuming this type exists
            else:
                 self.logger.error("Internal error: Could not determine command format for CommandExecutor.")
                 return False

            # --- Check Result ---
            # Adapt based on what CommandExecutor.execute returns (e.g., return code, CompletedProcess object)
            # Assuming it raises CalledProcessError on failure or returns a status code/object
            # Example check if it returns a simple success/failure boolean or status code:
            if isinstance(result, bool) and result:
                self.logger.info(f"SCP command executed successfully. Deployment presumed successful.")
                return True
            elif isinstance(result, int) and result == 0:
                 self.logger.info(f"SCP command executed with return code 0. Deployment presumed successful.")
                 return True
            elif hasattr(result, 'returncode') and result.returncode == 0:
                 self.logger.info(f"SCP command process completed with return code 0. Deployment presumed successful.")
                 return True
            else:
                 # Attempt to get stderr if available from result
                 stderr_info = getattr(result, 'stderr', 'No stderr captured') if result else 'Execution failed early'
                 self.logger.error(f"SCP command execution failed. Result: {result}. Stderr: {stderr_info}")
                 return False

        except subprocess.CalledProcessError as e:
            self.logger.error(f"SCP command failed with return code {e.returncode}. Error: {e.stderr or e.stdout or e}", exc_info=True)
            return False
        except FileNotFoundError:
            self.logger.error(f"Deployment failed: 'scp' command not found. Ensure SCP client is installed and in PATH.")
            return False
        except ValueError as e: # Catch potential config issues passed down
            self.logger.error(f"Deployment failed due to a value error: {e}", exc_info=True)
            return False
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred during deployment: {e}", exc_info=True)
            return False