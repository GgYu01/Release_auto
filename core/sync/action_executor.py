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
            self.logger.debug(f"Executing git_command action for repo: {git_repo_info.repo_name}")
            self.logger.debug(f"  Initial params: {params}")
            self.logger.debug(f"  GitRepoInfo.remote_name: {git_repo_info.remote_name}, GitRepoInfo.remote_branch: {git_repo_info.remote_branch}, GitRepoInfo.local_branch: {git_repo_info.local_branch}")

            updated_args = []

            for arg in params["args"]:
                if isinstance(arg, str) and "{local_branch}" in arg:
                    self.logger.debug("  Found {local_branch} placeholder in arg: " + arg)
                    replaced_arg = arg.format(local_branch=git_repo_info.local_branch)
                    self.logger.debug(f"    Replacing '{arg}' with '{replaced_arg}'")
                    updated_args.append(replaced_arg)
                elif isinstance(arg, str) and "{remote_name}" in arg and "{remote_branch}" in arg:
                    self.logger.debug("  Found {remote_name} and {remote_branch} placeholders in arg: " + arg)
                    replaced_arg = arg.format(remote_name=git_repo_info.remote_name, remote_branch=git_repo_info.remote_branch)
                    self.logger.debug(f"    Replacing '{arg}' with '{replaced_arg}'")
                    updated_args.append(replaced_arg)
                elif isinstance(arg, str) and "{remote_name}" in arg:
                    self.logger.debug("  Found {remote_name} placeholder in arg: " + arg)
                    replaced_arg = arg.format(remote_name=git_repo_info.remote_name)
                    self.logger.debug(f"    Replacing '{arg}' with '{replaced_arg}'")
                    updated_args.append(replaced_arg)
                elif isinstance(arg, str) and "{remote_branch}" in arg:
                    self.logger.debug("  Found {remote_branch} placeholder in arg: " + arg)
                    if git_repo_info.remote_branch is None:
                        self.logger.warning(f"Remote branch is not configured for repo: {git_repo_info.repo_name}. Placeholder {{remote_branch}} will be replaced with None.")
                        replaced_arg = arg.format(remote_branch=None)
                        self.logger.debug(f"    Replacing '{arg}' with '{replaced_arg}' (remote_branch is None)")
                        updated_args.append(replaced_arg)
                    else:
                        replaced_arg = arg.format(remote_branch=git_repo_info.remote_branch)
                        self.logger.debug(f"    Replacing '{arg}' with '{replaced_arg}'")
                        updated_args.append(replaced_arg)
                else:
                    updated_args.append(arg)

            params["args"] = updated_args
            self.logger.debug(f"  Final params before command execution: {params}")
            self.command_executor.execute(action.action_type, command_params=params)

        else:
            self.command_executor.execute(action_type=action.action_type, command_params=params)
