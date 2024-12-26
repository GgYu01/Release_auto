# repo_manager.py
from typing import List
from pathlib import Path
from utils.logger import Logger
from config.repo_config import REPO_CONFIGS, BaseRepositoryConfig

logger = Logger().logger

def initialize_repositories() -> List[BaseRepositoryConfig]:
    logger.info("开始初始化 Git 仓库信息...")
    repo_info_list: List[BaseRepositoryConfig] = []
    for repo_config in REPO_CONFIGS:
        repo_info = BaseRepositoryConfig(
            repo_name=repo_config.repo_name,
            repo_path=repo_config.repo_path,
            parent_repo=repo_config.parent_repo,
            is_independent=repo_config.is_independent,
            manifest_path=repo_config.manifest_path,
            tag_prefix=repo_config.tag_prefix,
            generate_patch=repo_config.generate_patch,
            analyze_commit=repo_config.analyze_commit,
            branch=repo_config.branch,
            patch_strict_mode=repo_config.patch_strict_mode,
            no_commit_analysis=repo_config.no_commit_analysis,
            git_remotes=repo_config.git_remotes,
            git_push_template=repo_config.git_push_template
        )
        logger.debug(f"已加载配置: {repo_config}")

        if repo_config.repo_name == "nebula" and repo_config.manifest_path:
            logger.info(f"开始处理 Nebula 仓库的 manifest 文件: {repo_config.manifest_path}")
            try:
                with open(repo_config.manifest_path, 'r') as f:
                    manifest_content = f.readlines()
                for line in manifest_content:
                    if 'reponame' in line:
                        repo_info.repo_name = line.split('=')[1].strip()
                    if 'rootpath' in line:
                        repo_info.repo_path = Path(line.split('=')[1].strip()).resolve()
                logger.info(f"Nebula 仓库信息从 manifest 文件更新: 仓库名={repo_info.repo_name}, 路径={repo_info.repo_path}")
            except Exception as e:
                logger.error(f"处理 Nebula 仓库 manifest 文件时出错: {e}")
            else:
                repo_info.repo_path = repo_info.repo_path.resolve()

        if repo_config.parent_repo:
            repo_info.parent_repo = repo_config.parent_repo
        if repo_config.is_independent is not None:
            repo_info.is_independent = repo_config.is_independent
        if repo_config.manifest_path:
            repo_info.manifest_path = repo_config.manifest_path
        if repo_config.tag_prefix:
            repo_info.tag_prefix = repo_config.tag_prefix
        if repo_config.generate_patch is not None:
            repo_info.generate_patch = repo_config.generate_patch
        if repo_config.analyze_commit is not None:
            repo_info.analyze_commit = repo_config.analyze_commit

        if repo_config.branch:
            if hasattr(repo_config, 'special_branch_rules') and isinstance(repo_config.special_branch_rules, dict):
                if repo_info.repo_name in repo_config.special_branch_rules:
                    repo_info.branch = repo_config.special_branch_rules[repo_info.repo_name]
                    logger.info(f"仓库 {repo_info.repo_name} 的分支切换为特殊分支: {repo_info.branch}")
            else:
                repo_info.branch = repo_config.branch

        repo_info_list.append(repo_info)
        logger.info(f"Git 仓库 {repo_info.repo_name} 信息初始化完成: {repo_info}")
    logger.info("Git 仓库信息初始化完成.")
    return repo_info_list
