from abc import ABC, abstractmethod
from config.schemas import GitRepoInfo, SyncStrategyConfig, SyncAction
from utils.command_executor import CommandExecutor
from utils.custom_logger import Logger
from config.sync_config import sync_strategies_config
from typing import Dict, List

class RepoSyncStrategy(ABC):
    def __init__(self):
       self.logger = Logger(name=self.__class__.__name__)

   @abstractmethod
   def sync(self, git_repo_info: GitRepoInfo, command_executor: CommandExecutor, config: SyncStrategyConfig):
       pass