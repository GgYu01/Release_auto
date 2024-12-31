from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class GitRepoInfo:
    repo_name: str
    repo_parent: str
    path: str
    repo_type: str
    tag_prefix: Optional[str] = None
    remote_name: Optional[str] = None
    remote_branch: Optional[str] = None
    parent_repo: Optional[str] = None
    commit_analyses: List[Dict] = field(default_factory=list)
    newest_version: Optional[str] = None
    next_newest_version: Optional[str] = None
    analyze_commit: bool = False
    generate_patch: bool = False
    branch_info: Optional[str] = None
    push_template: Optional[str] = None

@dataclass
class RepoConfig:
    repo_name: str
    repo_type: str
    path: str
    git_repos: List[GitRepoInfo] = field(default_factory=list)
    manifest_path: Optional[str] = None
    default_tag_prefix: Optional[str] = None
    parent_repo: Optional[str] = None
    manifest_type: Optional[str] = None
    default_analyze_commit: bool = False
    default_generate_patch: bool = False
    all_branches: List[str] = field(default_factory=list)
    special_branch_repos: Dict[str, str] = field(default_factory=dict)

@dataclass
class AllReposConfig:
    repo_configs: Dict[str, RepoConfig] = field(default_factory=dict)

    def all_git_repos(self):
        for repo_config in self.repo_configs.values():
            for git_repo in repo_config.git_repos:
                yield git_repo
