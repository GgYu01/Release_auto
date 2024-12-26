# main.py
from repo_manager import initialize_repositories
from utils.logger import Logger

logger = Logger().logger

if __name__ == "__main__":
    logger.info("程序开始运行...")
    repository_infos = initialize_repositories()
    logger.info("所有 Git 仓库信息初始化完毕。")
    # 可以根据需要对 repository_infos 进行后续处理
    for repo_info in repository_infos:
        logger.debug(f"最终的仓库信息: {repo_info}")
    logger.info("程序运行结束。")
