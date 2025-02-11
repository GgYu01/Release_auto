from utils.command_executor import CommandExecutor
from config.schemas import GitRepoInfo, SyncAction
from utils.custom_logger import Logger
from typing import Dict

class ActionExecutor:
    def __init__(self, command_executor: CommandExecutor):
        self.command_executor = command_executor
        self.logger = Logger(name="ActionExecutor")

    def execute_action(self, git_repo_info: GitRepoInfo, action: SyncAction):
        params = action.action_params.copy()
        if "path" in params:
            params["path"] = git_repo_info.repo_path + "/" + params["path"]
        params["cwd"] = git_repo_info.repo_path

        if action.action_type == "jiri_command":
            if params.get("command") == "runp":
                if params.get("args")[0] == "git":
                    if params.get("args")[1] == "remote":
                        self.command_executor.execute("jiri_command", {"jiri_path": git_repo_info.repo_path, "command": "runp", "args": ["git", "remote", "get-url", "origin"]})
                        self.command_executor.execute("jiri_command", {"jiri_path": git_repo_info.repo_path, "command": "runp", "args": ["sed", "s/gerrit/gerrit-review/"]})
                        self.command_executor.execute("jiri_command", {"jiri_path": git_repo_info.repo_path, "command": "runp", "args": ["xargs", "git", "remote", "set-url", "--push", "origin"]})
                    else:
                        self.command_executor.execute("jiri_command", {"jiri_path": git_repo_info.repo_path, "command": "runp", "args": params.get("args")})
                else:
                    self.command_executor.execute("jiri_command", {"jiri_path": git_repo_info.repo_path, "command": "runp", "args": params.get("args")})
            else:
                params["jiri_path"] = git_repo_info.repo_path
                self.command_executor.execute(action_type=action.action_type, command_params=params)
        elif action.action_type == "git_command":
            if "{local_branch}" in params.get("args", []):
                params["args"] = [arg.format(local_branch=git_repo_info.local_branch) if isinstance(arg, str) else arg for arg in params["args"]]
            if "{remote_branch}" in params.get("args", []):
                if git_repo_info.remote_branch is None:
                    self.logger.warning(f"Remote branch is not configured for repo: {git_repo_info.repo_name}, action: {action.action_type}. Placeholder {{remote_branch}} will be replaced with None.")
                    params["args"] = [arg.format(remote_branch=None) if isinstance(arg, str) else arg for arg in params["args"]]
                else:
                    params["args"] = [arg.format(remote_branch=git_repo_info.remote_branch) if isinstance(arg, str) else arg for arg in params["args"]]
            self.command_executor.execute(action.action_type, command_params=params)

        else:
            self.command_executor.execute(action_type=action.action_type, command_params=params)