import subprocess
import os
import shlex
from utils.custom_logger import Logger
from typing import Dict, List, Optional, Union

class CommandExecutor:
    def __init__(self) -> None:
        self.logger: Logger = Logger(name="CommandExecutor")
        # Start with a copy of the current process environment
        self._env: Dict[str, str] = os.environ.copy()

    def execute(self, command_type: str, command_params: Dict) -> Optional[subprocess.CompletedProcess]:
        try:
            executor_method = getattr(self, f"execute_{command_type}", None)
            if callable(executor_method):
                return executor_method(command_params)
            else:
                # Fallback for potentially unknown but simple types needing shell execution
                # Primarily for backward compatibility if needed, but prefer specific methods
                if command_type == "shell_command":
                     return self.execute_shell_command(command_params)
                self.logger.error(f"Unknown command type: {command_type}")
                return None
        except FileNotFoundError as e:
            self.logger.error(f"Command not found: {e}")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed with exit code {e.returncode}: {e.cmd}\nStderr: {e.stderr}")
            raise
        except Exception as e:
            # Catching generic Exception for broader error logging
            self.logger.exception(f"An unexpected error occurred during command execution: {e}")
            raise # Re-raise after logging

    def _run_subprocess(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        capture_output: bool = True,
        text: bool = True,
        check: bool = False, # Set to False to handle errors manually
        env: Optional[Dict[str, str]] = None,
        shell: bool = False # Default to False for security and correctness
    ) -> subprocess.CompletedProcess:

        effective_env = self._env.copy()
        if env:
            effective_env.update(env)

        # Expand user path for cwd if provided
        if cwd:
            cwd = os.path.expanduser(cwd)
            if not os.path.isdir(cwd):
                self.logger.error(f"Working directory does not exist: {cwd}")
                # Raise a specific error or handle as needed
                raise FileNotFoundError(f"Working directory not found: {cwd}")

        # Prepare command string for logging/error messages
        command_str = shlex.join(command) if not shell else command[0] # If shell=True, command should be a string
        self.logger.info(f"Executing: '{command_str}' in '{cwd or os.getcwd()}' (shell={shell})")

        try:
            result = subprocess.run(
                command if not shell else command_str, # Pass list for shell=False, string for shell=True
                capture_output=capture_output,
                text=text,
                cwd=cwd,
                env=effective_env,
                check=check, # Let caller handle check=True or manual check
                shell=shell
            )
            if result.returncode != 0:
                self.logger.error(f"Command failed: {command_str}\nStderr: {result.stderr}")
                # Raise error here to be caught by the main execute method or caller
                raise subprocess.CalledProcessError(result.returncode, command_str, output=result.stdout, stderr=result.stderr)
            self.logger.debug(f"Command output: {result.stdout}")
            return result
        except FileNotFoundError:
             self.logger.error(f"Executable not found for command: {command_str}")
             raise # Re-raise FileNotFoundError
        # Other exceptions will propagate

    def execute_git_command(self, params: Dict) -> subprocess.CompletedProcess:
        command_parts: List[str] = ["git", params["command"]] + params.get("args", [])
        cwd: Optional[str] = params.get("cwd")
        return self._run_subprocess(command=command_parts, cwd=cwd)

    def execute_jiri_command(self, params: Dict) -> subprocess.CompletedProcess:
        jiri_path: str = params.get("jiri_path", ".") # Consider making this mandatory or better default
        # Ensure jiri binary path is constructed correctly
        jiri_binary = os.path.join(jiri_path, ".jiri_root", "bin", "jiri")
        command_parts: List[str] = [jiri_binary, params["command"]] + params.get("args", [])
        # Jiri commands often assume execution within the jiri root
        return self._run_subprocess(command=command_parts, cwd=jiri_path)

    def execute_mkdir_command(self, params: Dict) -> subprocess.CompletedProcess:
        path: str = params["path"] # Expect path to be mandatory
        command_parts: List[str] = ["mkdir", "-p", path]
        # mkdir doesn't typically need a specific cwd unless path is relative
        return self._run_subprocess(command=command_parts)

    def execute_rm_command(self, params: Dict) -> subprocess.CompletedProcess:
        path: str = params["path"] # Expect path to be mandatory
        command_parts: List[str] = ["rm", "-rf", path]
        # rm doesn't typically need a specific cwd unless path is relative
        return self._run_subprocess(command=command_parts)

    def execute_source_command(self, params: Dict) -> None:
        # Renamed from implicit handling in execute_shell_command
        source_file: str = os.path.expanduser(params["args"][0])
        cwd: Optional[str] = params.get("cwd") # Pass cwd for sourcing if needed

        self.logger.info(f"Sourcing environment file: {source_file} in {cwd or 'current directory'}")
        if not os.path.isfile(source_file):
             self.logger.error(f"Source file not found: {source_file}")
             raise FileNotFoundError(f"Source file not found: {source_file}")

        try:
            # Use bash subshell to source and print env diff
            # 'set -a' exports all variables defined or modified by source
            env_cmd = f"set -a && source '{source_file}' && env"
            # Run in bash, capture output, use current executor env
            result = self._run_subprocess(
                command=['bash', '-c', env_cmd],
                cwd=cwd,
                env=self._env.copy(), # Use current env as base for sourcing
                shell=False # We explicitly call bash
            )

            # Parse the output of 'env' to update self._env
            # This overwrites/adds variables from the sourced script
            new_env = {}
            for line in result.stdout.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    new_env[key] = value

            # Update the executor's persistent environment state
            self._env.update(new_env)
            self.logger.info(f"Successfully sourced {source_file}. Updated environment.")
            # Source command itself doesn't return a process result in the same way
            # Return None or potentially the CompletedProcess of the bash command if useful
            return None # Explicitly return None as it modifies state

        except FileNotFoundError: # Catch if bash isn't found
            self.logger.error(f"Bash executable not found, cannot source file.")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to source {source_file}. Error: {e.stderr}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error sourcing {source_file}: {e}")
            raise

    def execute_shell_command(self, params: Dict) -> subprocess.CompletedProcess:
        command: Union[str, List[str]] = params["command"]
        args: List[str] = params.get("args", [])
        cwd: Optional[str] = params.get("cwd")
        env_vars: Dict[str, str] = params.get("env", {})
        use_shell: bool = params.get("shell", False) # Allow caller to force shell=True if needed

        # If command is already a list, use it directly (for shell=False)
        # If command is a string, prepare appropriately based on use_shell
        if isinstance(command, str):
            if use_shell:
                # For shell=True, join args into the command string
                full_command_str = f"{command} {' '.join(shlex.quote(arg) for arg in args)}"
                command_list_or_str = full_command_str # Pass string to _run_subprocess
            else:
                # For shell=False, command is the executable, args are separate
                command_list_or_str = [command] + args # Pass list to _run_subprocess
        elif isinstance(command, list):
             # If command is already a list, assume it's prepared for shell=False
             command_list_or_str = command + args # Combine base command list with extra args
             if use_shell:
                 self.logger.warning("Received command as list but shell=True requested. Joining list.")
                 command_list_or_str = shlex.join(command_list_or_str)
        else:
            raise TypeError("Command must be a string or list of strings")


        return self._run_subprocess(
            command=command_list_or_str, # Pass prepared list or string
            cwd=cwd,
            env=env_vars, # Pass specific env vars for this command
            shell=use_shell # Use specified shell setting
        )
