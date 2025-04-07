import subprocess
import os
import shlex
import pathlib
from utils.custom_logger import Logger
from typing import Dict, List, Optional, Union, Tuple, Any

class CommandExecutor:
    def __init__(self) -> None:
        self.logger: Logger = Logger(name="CommandExecutor")

    def _run_subprocess(
        self,
        command: Union[List[str], str],
        cwd: Optional[Union[str, pathlib.Path]] = None,
        capture_output: bool = True,
        text: bool = True,
        check: bool = True,
        env: Optional[Dict[str, str]] = None,
        shell: bool = False
    ) -> subprocess.CompletedProcess:

        effective_env = os.environ.copy()
        if env:
            effective_env.update(env)

        cwd_path: Optional[pathlib.Path] = None
        if cwd:
            cwd_path = pathlib.Path(cwd).expanduser()
            if not cwd_path.is_dir():
                self.logger.error(f"Working directory does not exist: {cwd_path}")
                raise FileNotFoundError(f"Working directory not found: {cwd_path}")

        if isinstance(command, list):
             command_str_for_log = shlex.join(command)
             command_to_run = command if not shell else command_str_for_log
        else: # command is str
             command_str_for_log = command
             command_to_run = command

        self.logger.info(
            f"Executing (shell={shell}): '{command_str_for_log}' "
            f"in '{cwd_path or pathlib.Path.cwd()}'"
        )

        executable_path = None
        if shell:
            executable_path = '/bin/bash'

        try:
            result = subprocess.run(
                command_to_run,
                capture_output=capture_output,
                text=text,
                cwd=str(cwd_path) if cwd_path else None,
                env=effective_env,
                check=False, # Check manually after logging
                shell=shell,
                executable=executable_path
            )

            if result.returncode != 0:
                stderr_output = result.stderr.strip() if result.stderr else "No stderr"
                stdout_output = result.stdout.strip() if result.stdout else "No stdout"
                self.logger.error(
                    f"Command failed with exit code {result.returncode}: {command_str_for_log}\n"
                    f"  Stderr: {stderr_output}\n"
                    f"  Stdout: {stdout_output}"
                )
                if check:
                    raise subprocess.CalledProcessError(
                        result.returncode, command_to_run,
                        output=result.stdout, stderr=result.stderr
                    )
            else:
                 # Log truncated stdout at debug level on success
                 stdout_preview = (result.stdout[:100] + '...') if result.stdout and len(result.stdout) > 100 else result.stdout
                 self.logger.debug(f"Command successful: {command_str_for_log}. Output preview: {stdout_preview}")


            return result
        except FileNotFoundError:
             self.logger.error(f"Executable not found for command: {command_str_for_log}")
             raise
        except Exception as e:
             self.logger.exception(f"An unexpected error occurred running {command_str_for_log}: {e}")
             raise


    def execute(
        self,
        command_type: str,
        command_params: Dict[str, Any],
        check: bool = True
        ) -> subprocess.CompletedProcess:
        try:
            executor_method = getattr(self, f"execute_{command_type}", None)
            if callable(executor_method):
                # Pass check to specific handlers if they need it
                return executor_method(command_params, check=check)
            else:
                 # Fallback for generic shell command execution if type unknown
                 if "command" in command_params:
                      self.logger.warning(f"Unknown command type '{command_type}', attempting generic shell execution.")
                      return self.execute_shell_command(command_params, check=check)
                 else:
                      self.logger.error(f"Unknown command type and no 'command' key: {command_type}")
                      raise ValueError(f"Invalid command specification for type: {command_type}")

        except FileNotFoundError as e:
            self.logger.error(f"Command or file not found: {e}")
            raise
        except subprocess.CalledProcessError as e:
            # Error is already logged by _run_subprocess if check=True there
            # If check=False was used internally, log here. Typically _run_subprocess handles it.
            if not check: # If check was initially False for execute() call
                 self.logger.error(f"Command failed (check=False): {e.cmd}\nStderr: {e.stderr}")
            raise
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred processing command type {command_type}: {e}")
            raise

    def execute_git_command(self, params: Dict, check: bool = True) -> subprocess.CompletedProcess:
        command_parts: List[str] = ["git", params["command"]] + params.get("args", [])
        cwd: Optional[str] = params.get("cwd")
        return self._run_subprocess(command=command_parts, cwd=cwd, check=check)

    def execute_jiri_command(self, params: Dict, check: bool = True) -> subprocess.CompletedProcess:
        jiri_path_str: str = params.get("jiri_path", ".")
        jiri_path = pathlib.Path(jiri_path_str).expanduser()
        jiri_binary = jiri_path / ".jiri_root" / "bin" / "jiri"
        command_parts: List[str] = [str(jiri_binary), params["command"]] + params.get("args", [])
        return self._run_subprocess(command=command_parts, cwd=jiri_path, check=check)

    def execute_mkdir_command(self, params: Dict, check: bool = True) -> subprocess.CompletedProcess:
        path: str = params["path"]
        target_path = pathlib.Path(path).expanduser()
        self.logger.info(f"Ensuring directory exists: {target_path}")
        target_path.mkdir(parents=True, exist_ok=True)
        # Return a dummy CompletedProcess for compatibility if needed, or adjust interface
        return subprocess.CompletedProcess(args=['mkdir', '-p', str(target_path)], returncode=0)


    def execute_rm_command(self, params: Dict, check: bool = True) -> subprocess.CompletedProcess:
        path_str: str = params["path"]
        target_path = pathlib.Path(path_str).expanduser()
        self.logger.info(f"Recursively removing path: {target_path}")
        import shutil
        try:
             if target_path.is_dir():
                  shutil.rmtree(target_path, ignore_errors=True)
             elif target_path.exists():
                  target_path.unlink(missing_ok=True)
             self.logger.debug(f"Successfully removed {target_path}")
             return subprocess.CompletedProcess(args=['rm', '-rf', str(target_path)], returncode=0)
        except Exception as e:
             self.logger.error(f"Failed to remove {target_path}: {e}")
             # Mimic CalledProcessError if check=True
             if check:
                  raise subprocess.CalledProcessError(1, ['rm', '-rf', str(target_path)]) from e
             return subprocess.CompletedProcess(args=['rm', '-rf', str(target_path)], returncode=1)


    def execute_shell_command(self, params: Dict, check: bool = True) -> subprocess.CompletedProcess:
        command: Union[str, List[str]] = params["command"]
        args: List[str] = params.get("args", [])
        cwd: Optional[str] = params.get("cwd")
        env_vars: Optional[Dict[str, str]] = params.get("env") # Allow None
        use_shell: bool = params.get("shell", False)

        command_list_or_str: Union[str, List[str]]

        if isinstance(command, str):
            if use_shell:
                # If shell=True, args should be incorporated directly into the command string
                # Ensure proper quoting if args are provided separately with a string command + shell=True
                if args:
                     quoted_args = ' '.join(shlex.quote(arg) for arg in args)
                     command_list_or_str = f"{command} {quoted_args}"
                else:
                     command_list_or_str = command
            else:
                # If shell=False, treat the string as the executable and args as parameters
                command_list_or_str = [command] + args
        elif isinstance(command, list):
             # If command is already a list, append args
             command_list_or_str = command + args
             if use_shell:
                  # If shell=True is explicitly requested with a list, join it into a string
                  self.logger.warning("Command is a list but shell=True requested. Joining list into a string.")
                  command_list_or_str = shlex.join(command_list_or_str)
        else:
            raise TypeError("Command must be a string or list of strings")


        return self._run_subprocess(
            command=command_list_or_str,
            cwd=cwd,
            env=env_vars,
            shell=use_shell,
            check=check
        )
