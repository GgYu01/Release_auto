import subprocess
from utils.custom_logger import Logger
from typing import Dict

class CommandExecutor:
    def __init__(self):
        self.logger = Logger(name="CommandExecutor")

    def execute(self, command_type: str, command_params: Dict):
        try:
            if command_type == "git_command":
                self.execute_git_command(command_params)
            elif command_type == "jiri_command":
                self.execute_jiri_command(command_params)
            elif command_type == "mkdir":
                self.execute_mkdir_command(command_params)
            elif command_type == "rm":
                self.execute_rm_command(command_params)
            else:
                self.logger.error(f"Unknown command type: {command_type}")
        except Exception as e:
            self.logger.exception(f"Error executing command: {e}")

    def execute_git_command(self, params: Dict):
        command = ["git"] + [params.get("command")] + params.get("args", [])
        cwd = params.get("cwd", None)  # Optional working directory
        self.logger.info(f"Executing git command: {command} in {cwd or 'default directory'}")
        result = subprocess.run(command, capture_output=True, text=True, cwd=cwd, check=False)
        if result.returncode != 0:
            self.logger.error(f"Git command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
        self.logger.debug(f"Git command output: {result.stdout}")

    def execute_jiri_command(self, params: Dict):
        jiri_path = params.get("jiri_path", ".")
        command = [f"{jiri_path}/.jiri_root/bin/jiri"] + [params.get("command")] + params.get("args", [])
        self.logger.info(f"Executing jiri command: {command}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=jiri_path)
        if result.returncode != 0:
            self.logger.error(f"Jiri command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
        self.logger.debug(f"Jiri command output: {result.stdout}")

    def execute_mkdir_command(self, params: Dict):
        path = params.get("path")
        self.logger.info(f"Executing mkdir command: {path}")
        result = subprocess.run(["mkdir", "-p", path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.logger.error(f"mkdir command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, ["mkdir", "-p", path], result.stderr)
        self.logger.debug(f"mkdir command output: {result.stdout}")

    def execute_rm_command(self, params: Dict):
        path = params.get("path")
        self.logger.info(f"Executing rm command: {path}")
        result = subprocess.run(["rm", "-rf", path], capture_output=True, text=True, check=False)  # Use -rf for recursive removal
        if result.returncode != 0:
            self.logger.error(f"rm command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, ["rm","-rf", path], result.stderr)
        self.logger.debug(f"rm command output: {result.stdout}")