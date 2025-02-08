from core.sync.action_executor import ActionExecutor
from config.schemas import AllReposConfig, GitRepoInfo, AllSyncConfigs
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from typing import Dict, Optional


class RepoSynchronizer:
    def __init__(self, all_repos_config: AllReposConfig, all_sync_configs: AllSyncConfigs, command_executor: CommandExecutor):
        self.all_repos_config = all_repos_config
        self.all_sync_configs = all_sync_configs
        self.command_executor = command_executor
        self.logger = Logger(name="RepoSynchronizer")

    def sync_repos(self):
        for git_repo_info in self.all_repos_config.all_git_repos():
            strategy_name = self.get_strategy_name(git_repo_info.repo_parent)
            if strategy_name:
                self.logger.info(f"Synchronizing repository: {git_repo_info.repo_name} with strategy: {strategy_name}")
                strategy_config = self.all_sync_configs.sync_configs.get(strategy_name)
                if not strategy_config:
                    self.logger.error(f"Synchronization configuration not found for strategy: {strategy_name}")
                    continue

                action_executor = ActionExecutor(self.command_executor)
                try:
                    for action in strategy_config.sync_actions:
                        action_executor.execute_action(git_repo_info, action)
                    self.logger.info(f"Successfully synchronized repository: {git_repo_info.repo_name}")
                except Exception as e:
                    self.logger.exception(f"Failed to synchronize repository: {git_repo_info.repo_name}, error: {e}")
            else:
                self.logger.warning(f"No synchronization strategy found for parent type: {git_repo_info.repo_parent}")


    def get_strategy_name(self, parent_type: str) -> Optional[str]:
        repo_config = self.all_repos_config.repo_configs.get(parent_type)
        return repo_config.sync_strategy if repo_config else None