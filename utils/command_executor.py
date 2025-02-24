import subprocess
from utils.custom_logger import Logger
from typing import Dict
import os

class CommandExecutor:
    def __init__(self):
        self.logger = Logger(name="CommandExecutor")
        self._env = os.environ.copy()

    def execute(self, command_type: str, command_params: Dict):
        try:
            if command_type == "git_command":
                return self.execute_git_command(command_params)
            elif command_type == "jiri_command":
                return self.execute_jiri_command(command_params)
            elif command_type == "mkdir":
                return self.execute_mkdir_command(command_params)
            elif command_type == "rm":
                return self.execute_rm_command(command_params)
            elif command_type == "shell_command":
                return self.execute_shell_command(command_params)
            else:
                self.logger.error(f"Unknown command type: {command_type}")
                return None
        except Exception as e:
            self.logger.exception(f"Error executing command: {e}")
            return None

    def execute_git_command(self, params: Dict):
        command = ["git"] + [params.get("command")] + params.get("args", [])
        cwd = params.get("cwd", None)
        self.logger.info(f"Executing git command: {command} in {cwd or 'default directory'}")
        result = subprocess.run(command, capture_output=True, text=True, cwd=cwd, check=False)
        if result.returncode != 0:
            self.logger.error(f"Git command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
        self.logger.debug(f"Git command output: {result.stdout}")
        return result

    def execute_jiri_command(self, params: Dict):
        jiri_path = params.get("jiri_path", ".")
        command = [f"{jiri_path}/.jiri_root/bin/jiri"] + [params.get("command")] + params.get("args", [])
        self.logger.info(f"Executing jiri command: {command}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=jiri_path)
        if result.returncode != 0:
            self.logger.error(f"Jiri command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
        self.logger.debug(f"Jiri command output: {result.stdout}")
        return result

    def execute_mkdir_command(self, params: Dict):
        path = params.get("path")
        self.logger.info(f"Executing mkdir command: {path}")
        result = subprocess.run(["mkdir", "-p", path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.logger.error(f"mkdir command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, ["mkdir", "-p", path], result.stderr)
        self.logger.debug(f"mkdir command output: {result.stdout}")
        return result

    def execute_rm_command(self, params: Dict):
        path = params.get("path")
        self.logger.info(f"Executing rm command: {path}")
        result = subprocess.run(["rm", "-rf", path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.logger.error(f"rm command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, ["rm","-rf", path], result.stderr)
        self.logger.debug(f"rm command output: {result.stdout}")
        return result

    def execute_shell_command(self, params: Dict):
        command = params.get("command")
        args = params.get("args", [])
        cwd = params.get("cwd", None)
        env_vars = params.get("env", {})

        # Handle environment variables
        if command == "export":
            for arg in args:
                key, value = arg.split("=", 1)
                self._env[key] = value
            return None

        # Handle source command
        if command == "source":
            source_file = os.path.expanduser(args[0])
            self.logger.info(f"Sourcing file: {source_file}")
            try:
                with open(source_file, 'r') as f:
                    content = f.read()
                # Execute the content in a subshell and capture the environment
                env_cmd = f"set -a && source {source_file} && env"
                result = subprocess.run(['bash', '-c', env_cmd], capture_output=True, text=True, env=self._env)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if '=' in line:
                            key, value = line.split('=', 1)
                            self._env[key] = value
                return result
            except Exception as e:
                self.logger.error(f"Failed to source {source_file}: {e}")
                raise

        # Handle cd command
        if command == "cd":
            target_dir = os.path.expanduser(args[0])
            self.logger.info(f"Changing directory to: {target_dir}")
            os.chdir(target_dir)
            return None

        # Handle other shell commands
        full_command = [command] + args
        self.logger.info(f"Executing shell command: {full_command} in {cwd or 'current directory'}")
        
        # Update environment with any new variables
        cmd_env = self._env.copy()
        cmd_env.update(env_vars)
        
        result = subprocess.run(full_command, capture_output=True, text=True, cwd=cwd, env=cmd_env, shell=True)
        if result.returncode != 0:
            self.logger.error(f"Shell command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, full_command, result.stderr)
        self.logger.debug(f"Shell command output: {result.stdout}")
        return result
