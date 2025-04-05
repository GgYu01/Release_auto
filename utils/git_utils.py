from typing import List, Optional, Dict, Any, Union
from utils.custom_logger import Logger
import os
import git


class GitOperator:
    def __init__(self, command_executor=None):
        self.logger = Logger(name=self.__class__.__name__)
        self._repo_cache = {}

    def _get_repo(self, repository_path: str) -> git.Repo:
        if repository_path not in self._repo_cache:
            try:
                self._repo_cache[repository_path] = git.Repo(repository_path)
            except git.InvalidGitRepositoryError:
                self.logger.error(f"Invalid git repository: {repository_path}")
                raise
            except Exception as e:
                self.logger.error(f"Error accessing git repository: {e}")
                raise
        
        return self._repo_cache[repository_path]

    def safe_add(self, repository_path: str, paths_to_add: List[str]) -> bool:
        try:
            self.logger.info(f"Adding files to git in {repository_path}")
            repo = self._get_repo(repository_path)
            
            for path in paths_to_add:
                full_path = os.path.join(repository_path, path) if not os.path.isabs(path) else path
                self.logger.info(f"Adding: {full_path}")
                
                try:
                    repo.git.add(path)
                except git.GitCommandError as e:
                    self.logger.error(f"Failed to add path: {path}. Error: {e}")
                    return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Error during git add operation: {e}")
            return False


    def commit_with_author(self, repository_path: str, commit_message: str, author: str) -> bool:
        try:
            self.logger.info(f"Committing changes in {repository_path}")
            repo = self._get_repo(repository_path)
            
            try:
                repo.git.commit(m=commit_message, author=author)
                self.logger.info(f"Successfully committed changes with message: {commit_message}")
                return True
            except git.GitCommandError as e:
                if "nothing to commit" in str(e):
                    self.logger.info("Nothing to commit, working tree clean")
                    return True
                self.logger.error(f"Git commit failed: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Error during git commit operation: {e}")
            return False

    def push_to_remote(self, repository_path: str, remote_name: str, local_branch: str, remote_branch: str) -> bool:
        try:
            self.logger.info(f"Pushing changes to {remote_name}/{remote_branch} from {repository_path}")
            repo = self._get_repo(repository_path)
            
            try:
                refspec = f"{local_branch}:{remote_branch}"
                repo.git.push(remote_name, refspec)
                self.logger.info(f"Successfully pushed changes to {remote_name}/{remote_branch}")
                return True
            except git.GitCommandError as e:
                self.logger.error(f"Git push failed: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Error during git push operation: {e}")
            return False


    def check_git_status(self, repository_path: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Checking git status in {repository_path}")
            repo = self._get_repo(repository_path)
            
            try:
                status_output = repo.git.status(porcelain=True)
                has_changes = bool(status_output.strip())
                
                return {
                    "success": True,
                    "has_changes": has_changes,
                    "status_output": status_output
                }
            except git.GitCommandError as e:
                self.logger.error(f"Failed to get git status: {e}")
                return {"success": False, "has_changes": False}
        except Exception as e:
            self.logger.error(f"Error checking git status: {e}")
            return {"success": False, "has_changes": False, "error": str(e)}

    def checkout_branch(self, repository_path: str, branch_name: str, create: bool = False) -> bool:
        try:
            self.logger.info(f"Checking out branch {branch_name} in {repository_path}")
            repo = self._get_repo(repository_path)
            
            try:
                if create:
                    repo.git.checkout(b=branch_name)
                else:
                    repo.git.checkout(branch_name)
                self.logger.info(f"Successfully checked out branch: {branch_name}")
                return True
            except git.GitCommandError as e:
                self.logger.error(f"Git checkout failed: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Error during git checkout operation: {e}")
            return False

    def get_current_branch(self, repository_path: str) -> Union[str, None]:
        try:
            repo = self._get_repo(repository_path)
            return repo.active_branch.name
        except Exception as e:
            self.logger.error(f"Failed to get current branch: {e}")
            return None

    def get_commit_history(self, repository_path: str, max_count: int = 10) -> List[Dict[str, str]]:
        try:
            repo = self._get_repo(repository_path)
            commits = []
            
            for commit in repo.iter_commits(max_count=max_count):
                commits.append({
                    "hash": commit.hexsha,
                    "author": f"{commit.author.name} <{commit.author.email}>",
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip()
                })
                
            return commits
        except Exception as e:
            self.logger.error(f"Failed to get commit history: {e}")
            return []
