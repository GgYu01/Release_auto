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

        if action.action_type == "git_command":
            self.logger.debug(f"Executing git_command action for repo: {git_repo_info.repo_name}")
            self.logger.debug(f"  Initial params: {params}")
            self.logger.debug(f"  GitRepoInfo.remote_name: {git_repo_info.remote_name}, GitRepoInfo.remote_branch: {git_repo_info.remote_branch}, GitRepoInfo.local_branch: {git_repo_info.local_branch}")

            updated_args = []

            placeholders = ["local_branch", "remote_name", "remote_branch"]

            for arg in params["args"]:
                if not isinstance(arg, str):
                    updated_args.append(arg)
                    continue

                format_kwargs = {}

                for placeholder_key in placeholders:
                    placeholder_str = "{" + placeholder_key + "}"
                    if placeholder_str in arg:
                        self.logger.debug(f"  Found {placeholder_str} placeholder in arg: {arg}")
                        placeholder_value = getattr(git_repo_info, placeholder_key)
                        
                        if placeholder_value is None:
                            self.logger.warning(f"{placeholder_key} is not configured for repo: {git_repo_info.repo_name}. Placeholder {placeholder_str} will be replaced with None.")
                        
                        format_kwargs[placeholder_key] = placeholder_value
                        self.logger.debug(f"    Adding {placeholder_key}={placeholder_value} to format_kwargs")

                if format_kwargs:
                    replaced_arg = arg.format(**format_kwargs)
                    self.logger.debug(f"    Replacing '{arg}' with '{replaced_arg}'")
                    updated_args.append(replaced_arg)
                else:
                    updated_args.append(arg)

            params["args"] = updated_args
            self.logger.debug(f"  Final params before command execution: {params}")
            self.command_executor.execute(action.action_type, command_params=params)

        else:
            self.command_executor.execute(action_type=action.action_type, command_params=params)
