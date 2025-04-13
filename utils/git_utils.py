import re
from urllib.parse import urlparse
from typing import List, Optional, Dict, Any, Union
from utils.custom_logger import Logger
from utils.command_executor import CommandExecutor
import subprocess
import os

class GitOperator:
    def __init__(self, command_executor: CommandExecutor):
        self.logger = Logger(name=self.__class__.__name__)
        if not command_executor:
            raise ValueError("CommandExecutor instance is required")
        self.command_executor = command_executor

    def _execute_git(self, repository_path: str, command: str, args: List[str]) -> subprocess.CompletedProcess:
        params = {
            "command": command,
            "args": args,
            "cwd": repository_path
        }
        return self.command_executor.execute("git_command", params)

    def safe_add(self, repository_path: str, paths_to_add: List[str]) -> bool:
        try:
            self.logger.info(f"Adding files to git in {repository_path}: {paths_to_add}")
            self._execute_git(repository_path, "add", paths_to_add)
            self.logger.info(f"Successfully added files in {repository_path}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error during git add operation in {repository_path}: {e.stderr}")
            return False
        except ValueError as e:
            self.logger.error(f"Configuration error for git add in {repository_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during git add operation in {repository_path}: {e}")
            return False

    def commit_with_author(self, repository_path: str, commit_message: str, author: str) -> bool:
        try:
            self.logger.info(f"Committing changes in {repository_path} with author {author}")
            args = ["-m", commit_message, f"--author={author}"]
            self._execute_git(repository_path, "commit", args)
            self.logger.info(f"Successfully committed changes in {repository_path} with message: {commit_message}")
            return True
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in e.stderr.lower() or "no changes added to commit" in e.stderr.lower():
                self.logger.info(f"Nothing to commit in {repository_path}")
                return True
            self.logger.error(f"Git commit failed in {repository_path}: {e.stderr}")
            return False
        except ValueError as e:
            self.logger.error(f"Configuration error for git commit in {repository_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during git commit operation in {repository_path}: {e}")
            return False

    def push_to_remote(self, repository_path: str, remote_name: str, local_branch: str, remote_branch: str) -> bool:
        try:
            self.logger.info(f"Pushing {local_branch} to {remote_name}/{remote_branch} from {repository_path}")
            refspec = f"{local_branch}:{remote_branch}"
            args = [remote_name, refspec]
            self._execute_git(repository_path, "push", args)
            self.logger.info(f"Successfully pushed to {remote_name}/{remote_branch} from {repository_path}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git push failed for {repository_path}: {e.stderr}")
            return False
        except ValueError as e:
            self.logger.error(f"Configuration error for git push in {repository_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during git push operation in {repository_path}: {e}")
            return False

    def check_git_status(self, repository_path: str) -> Dict[str, Any]:
        status_info = {"success": False, "has_changes": False, "status_output": "", "error": None}
        try:
            self.logger.info(f"Checking git status in {repository_path}")
            result = self._execute_git(repository_path, "status", ["--porcelain"])
            output = result.stdout.strip()
            status_info["status_output"] = output
            status_info["has_changes"] = bool(output)
            status_info["success"] = True
            self.logger.info(f"Git status check successful for {repository_path}. Has changes: {status_info['has_changes']}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get git status for {repository_path}: {e.stderr}")
            status_info["error"] = e.stderr
        except ValueError as e:
            self.logger.error(f"Configuration error for git status in {repository_path}: {e}")
            status_info["error"] = str(e)
        except Exception as e:
            self.logger.error(f"Unexpected error checking git status for {repository_path}: {e}")
            status_info["error"] = str(e)
        return status_info

    def checkout_branch(self, repository_path: str, branch_name: str, create: bool = False) -> bool:
        try:
            action = "Creating and checking out" if create else "Checking out"
            self.logger.info(f"{action} branch {branch_name} in {repository_path}")
            args = ["checkout"]
            if create:
                args.append("-b")
            args.append(branch_name)
            self._execute_git(repository_path, "checkout", args)
            self.logger.info(f"Successfully checked out branch: {branch_name} in {repository_path}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git checkout failed for branch {branch_name} in {repository_path}: {e.stderr}")
            return False
        except ValueError as e:
            self.logger.error(f"Configuration error for git checkout in {repository_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during git checkout operation in {repository_path}: {e}")
            return False

    def get_current_branch(self, repository_path: str) -> Union[str, None]:
        try:
            self.logger.info(f"Getting current branch for {repository_path}")
            result = self._execute_git(repository_path, "rev-parse", ["--abbrev-ref", "HEAD"])
            branch_name = result.stdout.strip()
            if branch_name == "HEAD":
                 self.logger.warning(f"Repository {repository_path} is in a detached HEAD state.")
                 try:
                    result_fallback = self._execute_git(repository_path, "branch", ["--show-current"])
                    branch_name = result_fallback.stdout.strip()
                    if branch_name:
                       self.logger.info(f"Determined branch {branch_name} using fallback command.")
                       return branch_name
                 except Exception:
                    pass 
                 return None 
            self.logger.info(f"Current branch for {repository_path} is {branch_name}")
            return branch_name
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get current branch for {repository_path}: {e.stderr}")
            return None
        except ValueError as e:
            self.logger.error(f"Configuration error getting current branch in {repository_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting current branch for {repository_path}: {e}")
            return None

    def get_commit_history(self, repository_path: str, max_count: int = 10) -> List[Dict[str, str]]:
        commits = []
        try:
            self.logger.info(f"Fetching commit history (max {max_count}) for {repository_path}")
            format_string = "%H%x00%an <%ae>%x00%aI%x00%s"
            args = ["log", f"--max-count={max_count}", f"--pretty=format:{format_string}"]
            result = self._execute_git(repository_path, "log", args)
            output = result.stdout.strip()

            if not output:
                self.logger.info(f"No commit history found for {repository_path}")
                return []

            lines = output.split('\n')
            for line in lines:
                if not line:
                    continue
                parts = line.split('\x00')
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3].strip()
                    })
                else:
                     self.logger.warning(f"Skipping malformed commit line in {repository_path}: {line}")

            self.logger.info(f"Successfully retrieved {len(commits)} commits for {repository_path}")
            return commits
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get commit history for {repository_path}: {e.stderr}")
            return []
        except ValueError as e:
            self.logger.error(f"Configuration error getting commit history in {repository_path}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting commit history for {repository_path}: {e}")
            return []

    def get_commit_message(self, repository_path: str, commit_hash: str) -> Optional[str]:
        try:
            self.logger.info(f"Getting commit message for {commit_hash} in {repository_path}")
            args = ["show", "-s", "--format=%B", commit_hash]
            result = self._execute_git(repository_path, "show", args)
            message = result.stdout.strip()
            self.logger.info(f"Successfully retrieved commit message for {commit_hash}")
            return message
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get commit message for {commit_hash} in {repository_path}: {e.stderr}")
            return None
        except ValueError as e:
            self.logger.error(f"Configuration error getting commit message in {repository_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting commit message for {commit_hash} in {repository_path}: {e}")
            return None

    def get_remote_url(self, repository_path: str, remote_name: str) -> Optional[str]:
        try:
            self.logger.info(f"Getting URL for remote '{remote_name}' in {repository_path}")
            args = ["remote", "get-url", remote_name]
            result = self._execute_git(repository_path, "remote", args)
            url = result.stdout.strip()
            self.logger.info(f"Successfully retrieved URL for remote '{remote_name}': {url}")
            return url
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get URL for remote '{remote_name}' in {repository_path}: {e.stderr}")
            return None
        except ValueError as e:
            self.logger.error(f"Configuration error getting remote URL in {repository_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting remote URL for '{remote_name}' in {repository_path}: {e}")
            return None


    def get_commits_between(self, repository_path: str, start_ref: str, end_ref: str) -> List[Dict[str, str]]:
        commit_details = []
        try:
            self.logger.info(f"Fetching commits between {start_ref} and {end_ref} in {repository_path}")
            # Format: Hash<NULL>AuthorName<NULL>AuthorEmail<NULL>Body<RECORD_SEPARATOR>
            format_string = "%H%x00%an%x00%ae%x00%B%x1E"
            # Git log command: git log start_ref..end_ref --pretty=format:...
            # Note: The range start_ref..end_ref excludes start_ref and includes end_ref.
            range_spec = f"{start_ref}..{end_ref}"
            args = [range_spec, f"--pretty=format:{format_string}"]

            result = self._execute_git(repository_path, "log", args)
            raw_output = result.stdout

            if not raw_output:
                self.logger.info(f"No commits found between {start_ref} and {end_ref} in {repository_path}")
                return []

            # Split commits using the Record Separator (\x1E)
            # Strip potential leading/trailing separators before splitting
            raw_commits = raw_output.strip().strip('\x1E').split('\x1E')

            for raw_commit in raw_commits:
                if not raw_commit:
                    continue
                # Split fields using the Null byte (\x00)
                parts = raw_commit.split('\x00')
                if len(parts) == 4:
                    commit_details.append({
                        'id': parts[0],
                        'author': f"{parts[1]} <{parts[2]}>",
                        'message': parts[3].strip()
                    })
                else:
                    # Log potentially sensitive commit data carefully (e.g., truncate)
                    log_data = raw_commit[:100] + '...' if len(raw_commit) > 100 else raw_commit
                    self.logger.warning(f"Skipping malformed commit data in {repository_path} between {start_ref}..{end_ref}. Parts found: {len(parts)}. Data snippet: {log_data}")

            self.logger.info(f"Successfully retrieved {len(commit_details)} commits between {start_ref} and {end_ref} in {repository_path}")
            return commit_details

        except subprocess.CalledProcessError as e:
            # Handle specific git errors like non-existent refs
            stderr_lower = e.stderr.lower()
            if "unknown revision or path not in the working tree" in stderr_lower or "invalid object name" in stderr_lower:
                 self.logger.warning(f"Could not find refs {start_ref} or {end_ref} in {repository_path}. Error: {e.stderr.strip()}")
            else:
                self.logger.error(f"Git log command failed for {repository_path} between {start_ref}..{end_ref}: {e.stderr.strip()}")
            return []
        except ValueError as e: # Catch errors from _execute_git
            self.logger.error(f"Configuration error getting commits between {start_ref}..{end_ref} in {repository_path}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting commits between {start_ref}..{end_ref} in {repository_path}: {e}", exc_info=True)
            return []



    def format_patch(self, repository_path: str, start_ref: str, end_ref: str, output_dir: str) -> List[str]:
        """
        Generates patch files for commits between start_ref and end_ref.

        Args:
            repository_path: The path to the git repository.
            start_ref: The starting commit reference (exclusive).
            end_ref: The ending commit reference (inclusive).
            output_dir: The directory to save the generated patch files.

        Returns:
            A list of absolute paths to the generated patch files, or an empty list on failure.
        """
        patch_files: List[str] = []
        try:
            self.logger.info(f"Generating patches for {repository_path} between {start_ref}..{end_ref} into {output_dir}")

            # Ensure output directory exists (though git format-patch should create it)
            os.makedirs(output_dir, exist_ok=True)

            range_spec = f"{start_ref}..{end_ref}"
            args = [range_spec, "--output-directory", output_dir]

            # Execute format-patch command
            self._execute_git(repository_path, "format-patch", args)

            # Git format-patch doesn't reliably output filenames if it fails partially.
            # So, we list the directory contents *after* successful execution.
            self.logger.info(f"Git format-patch command executed successfully for {repository_path}. Checking output directory...")

            for filename in os.listdir(output_dir):
                if filename.endswith(".patch"):
                    # Construct absolute path
                    full_path = os.path.abspath(os.path.join(output_dir, filename))
                    patch_files.append(full_path)

            if not patch_files:
                 self.logger.warning(f"format-patch command ran for {repository_path}, but no .patch files were found in {output_dir}. Range {start_ref}..{end_ref} might be empty or contain no changes.")
            else:
                 self.logger.info(f"Successfully generated {len(patch_files)} patch files in {output_dir} for {repository_path}")

            return patch_files

        except subprocess.CalledProcessError as e:
            stderr_lower = e.stderr.lower()
            if "unknown revision or path not in the working tree" in stderr_lower or "invalid object name" in stderr_lower:
                self.logger.warning(f"Could not generate patches for {repository_path}: Invalid refs {start_ref} or {end_ref}. Error: {e.stderr.strip()}")
            elif "did not produce patches" in stderr_lower:
                 self.logger.warning(f"Git format-patch command for {repository_path} indicated no patches were produced (range {start_ref}..{end_ref} likely empty or no changes). Error: {e.stderr.strip()}")
            else:
                self.logger.error(f"Git format-patch command failed for {repository_path}: {e.stderr.strip()}")
            return []
        except ValueError as e: # Catch errors from _execute_git
            self.logger.error(f"Configuration error during format-patch for {repository_path}: {e}")
            return []
        except FileNotFoundError:
             self.logger.error(f"Error during format-patch: Repository path {repository_path} or output directory {output_dir} not found after attempted creation.")
             return []
        except Exception as e:
            self.logger.error(f"Unexpected error during format-patch for {repository_path}: {e}", exc_info=True)
            return []


def parse_gerrit_remote_info(remote_url: str) -> Dict[str, Optional[str]]:
    parsed_url = urlparse(remote_url)
    info = {
        'user': None,
        'host': None,
        'port': None
    }
    if parsed_url.scheme == 'ssh':
        info['host'] = parsed_url.hostname
        info['user'] = parsed_url.username
        info['port'] = str(parsed_url.port) if parsed_url.port else '29418' # Default Gerrit SSH port
    # Add handling for other potential URL formats if necessary
    return info

def extract_change_id(commit_message: str) -> Optional[str]:
    match = re.search(r'^\s*Change-Id:\s*(I[0-9a-f]{40})\s*$', commit_message, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1)
    return None
