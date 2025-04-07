**项目名称:** GR Release Automation Tool

**1. 项目概述与目标 (Project Overview & Goals)**

*   **核心目标:** 创建一个自动化的 Python 工具，用于管理涉及多个代码仓库（独立 Git、Jiri 管理、Repo 管理）的复杂发布流程。该流程包括代码同步、构建（区分不同环境如 HEE/TEE）、版本标记（打 Tag）、变更分析、补丁生成、产物打包和发布。
*   **解决痛点:** 取代原有参数硬编码、手动操作繁琐、易出错的 Bash 脚本，提高发布流程的效率、可靠性和可维护性。
*   **关键特性:**
    *   **多仓库统一管理:** 无缝处理不同类型（Git, Jiri, Repo）和来源的代码仓库。
    *   **配置驱动:** 通过 Python 配置文件集中管理仓库信息、构建参数、发布选项、分支策略、标签规则等。
    *   **模块化设计:** 功能分离，易于理解、维护和扩展。
    *   **自动化流程:** 最小化人工干预，实现端到端的发布操作。
    *   **健壮性:** 包含详细日志、错误处理和状态反馈。

**2. 设计理念 (Design Philosophy)**

*   **配置优于编码:** 尽可能将易变信息（路径、分支名、标签格式、开关等）放入配置文件，代码负责实现核心逻辑。
*   **显式优于隐式:** 配置项和代码逻辑应清晰表达意图，避免依赖模糊的约定或本地环境状态（如尽量不依赖本地未提交的修改）。
*   **关注点分离:** 将仓库管理、命令执行、同步、构建、打标、分析、打包等功能解耦到独立的模块/类中。
*   **抽象与封装:** 底层操作（如 `git`, `jiri`, `repo`, 文件操作）被封装在工具类中，上层逻辑调用这些抽象接口。
*   **可扩展性:** 方便添加新的仓库类型、同步策略、构建步骤或发布目标。

**3. 系统架构 (System Architecture)**

该系统主要由以下几个核心组件构成：

*   **配置层 (`config/`)**:
    *   `schemas.py`: 定义所有配置项的数据结构 (Data Classes)，提供类型安全和默认值。
    *   `repos_config.py`: 定义所有代码仓库的元数据（路径、类型、分支、所属父仓库等）。
    *   `sync_config.py`: 定义不同仓库类型的同步策略和具体操作步骤。
    *   `tagging_config.py`: 定义打标签相关的全局配置（时区、手动版本号等）。
    *   `logging_config.py`: 定义日志输出配置。
    *   `BuildConfig` (in `schemas.py`): 定义构建相关的路径、Git 参数、不同构建类型（nebula-sdk, nebula, TEE）及其开关。
    *   *(未来可能)* `ReleaseConfig.py`: 定义发布相关的全局参数（目标 TAG、描述、CR、Excel 路径、打包规则、发布目标服务器等）。
    *   *(未来可能)* `AnalysisConfig.py`: 定义 Commit 分析和 Patch 生成的规则（特殊标记、强制覆盖规则等）。

*   **核心逻辑层 (`core/`)**:
    *   `repo_manager.py` (`RepoManager`): 负责根据配置加载和初始化仓库信息，包括解析 Jiri/Repo manifest 文件，填充 `GitRepoInfo` 对象。
    *   `repo_updater.py` (`RepoPropertyUpdater`): 负责根据父仓库配置更新子仓库的属性（如继承默认分支、标签前缀等）。
    *   `sync/` (`RepoSynchronizer`, `ActionExecutor`): 根据 `sync_config.py` 中的策略，执行代码同步操作（checkout, pull, reset, clean 等）。
    *   `builder.py` (`BuildSystem`): 负责执行具体的构建流程（nebula-sdk, nebula, TEE），包括环境准备、调用构建脚本/命令、文件操作和构建后的 Git 提交/推送。
    *   `tagger.py` (`Tagger`): 负责为仓库生成并应用 Git 标签，支持自动生成版本号（基于日期和序列）或使用手动指定的版本号。
    *   `git_tag_manager.py` (`GitTagFetcher`): 负责从 Git 仓库获取标签信息，特别是最新的和次新的标签，用于后续分析或版本确定。
    *   *(未来需要)* `analyzer.py` (`CommitAnalyzer`): 负责分析指定版本范围内的 Git Commit，提取信息，识别特殊标记。
    *   *(未来需要)* `patch_generator.py` (`PatchGenerator`): 负责根据 Commit 分析结果生成 Patch 文件。
    *   *(未来需要)* `packager.py` (`ReleasePackager`): 负责根据配置将分析结果（Commit Log, Patches）和构建产物打包成发布件。
    *   *(未来需要)* `reporter.py` (`ExcelReporter`): 负责将 Commit 信息写入指定的 Excel 文件。
    *   *(未来需要)* `deployer.py` (`Deployer`): 负责将打包好的发布件传输到目标服务器。

*   **工具层 (`utils/`)**:
    *   `command_executor.py` (`CommandExecutor`): 统一执行外部命令（Shell, Git, Jiri 等），提供日志记录和错误处理。
    *   `custom_logger.py` (`Logger`): 提供基于 Loguru 的日志记录功能。
    *   `file_utils.py` (`FileOperator`, `construct_path`): 封装文件和目录操作。
    *   `git_utils.py` (`GitOperator`): 封装常用的 Git 命令，提供更健壮的接口。
    *   `tag_utils.py`: 提供版本标识符解析和生成的辅助函数。

*   **入口 (`release.py`)**:
    *   应用程序的主入口点。
    *   负责解析命令行参数（*未来可能*）。
    *   初始化所有组件。
    *   根据配置和参数编排执行流程（同步 -> (打标?) -> 构建 -> (分析?) -> (打标?) -> (打包?) -> (发布?)）。*注意：当前代码中同步和打标在主流程被注释，构建是主要执行部分。*

**4. 已实现功能详解 (Implemented Features Details)**

*   **配置驱动的仓库管理:**
    *   通过 `repos_config.py` 和 `RepoConfig`/`GitRepoInfo` schema 定义仓库。
    *   `RepoManager` 能够解析 Git、Jiri、Repo 类型仓库，并为每个 Git 子仓库创建 `GitRepoInfo` 实例。
    *   `RepoPropertyUpdater` 确保子仓库继承父仓库的默认配置（如分支、标签前缀）。
    *   支持为 Jiri/Repo manifest 中的特定子仓库配置特殊的分支 (`special_branch_repos`)。
*   **灵活的代码同步:**
    *   `RepoSynchronizer` 结合 `sync_config.py` 实现不同步策略。
    *   `ActionExecutor` 负责执行同步策略中定义的具体动作（git fetch, checkout, reset, clean, pull 等）。
    *   同步操作使用占位符 (`{local_branch}`, `{remote_name}`, `{remote_branch}`)，动态替换为仓库的具体信息。
*   **模块化的构建系统 (`BuildSystem`):**
    *   区分 `nebula-sdk`, `nebula`, `TEE` 三种构建类型，逻辑分离在不同方法中。
    *   通过 `BuildConfig` 控制是否启用特定构建、构建前清理、构建后 Git 操作。
    *   封装了调用 `gr-nebula.py`, `gr-android.py`, `configure.sh`, `build_all.sh` 等外部脚本的逻辑。
    *   集成了 `FileOperator` 进行必要的文件复制（如 `zircon.elf`, `nebula*.bin`）和目录创建/清理。
    *   为每种构建类型实现了独立的 Git 操作（add, commit, push），使用不同的提交信息模板和目标分支/路径（定义在 `BuildGitConfig`）。
    *   构建环境（如 `PATH`, `SDK_APP_DIR` for `build_all.sh`）在执行命令时动态设置。
*   **版本标签管理:**
    *   `GitTagFetcher` 能够获取远程仓库的标签，并根据创建日期排序，找出最新和次新标签（考虑 `tag_prefix`）。
    *   `Tagger` 能够为所有配置的仓库打标签：
        *   支持通过 `TaggingConfig` 手动指定版本标识符 (`manual_version_identifier`)。
        *   若未手动指定，则自动生成 `YYYY_MMDD_NN` 格式的版本标识符，`NN` 基于当天已存在的标签自动递增。
        *   使用配置的时区 (`timezone`) 确定当前日期。
*   **健壮的底层工具:**
    *   `CommandExecutor` 提供了统一的命令执行接口，包含详细的日志（执行命令、目录、成功/失败、输出预览/错误信息）。
    *   `GitOperator` 封装了 Git 命令，提高了易用性和可靠性（如处理 "nothing to commit" 的情况）。
    *   `FileOperator` 提供了带日志和错误处理的文件操作。
    *   `Logger` 提供统一、可配置的日志记录。

**5. 未来工作 / 待实现功能 (Future Work / Missing Features)**

根据你的设计思路，以下功能是后续需要开发或完善的：

*   **Commit 分析 (`core/analyzer.py`):**
    *   实现 `GitOperator.get_commits_between(tag1, tag2)`。
    *   实现 `CommitAnalyzer` 类，根据 `GitRepoInfo` 的 `analyze_commit` 标志，调用 `get_commits_between`。
    *   解析 Commit 消息，识别特殊标记（需要定义标记规则）。
    *   在 `GitRepoInfo` 中存储分析结果（Commit 列表，包含 ID、消息、作者、日期、特殊标记等）。
*   **Patch 生成 (`core/patch_generator.py`):**
    *   实现 `PatchGenerator` 类。
    *   根据 `GitRepoInfo` 的 `generate_patch` 标志和 Commit 分析结果。
    *   调用 `git format-patch` 生成 Patch 文件（区分是针对特殊 Commit 还是整个范围）。
    *   将生成的 Patch 文件路径记录到 `GitRepoInfo` 的 Commit 分析结果中。
    *   实现临时 Patch 文件的管理和清理。
    *   实现 Patch 路径强制覆盖逻辑（根据配置将特定 Patch 应用到其他仓库的 Commit 记录中）。
*   **Excel 报告 (`core/reporter.py`):**
    *   引入 Excel 操作库（如 `openpyxl`）。
    *   实现 `ExcelReporter` 类，读取配置的 Excel 模板或路径。
    *   将 `CommitAnalyzer` 生成的 Commit 信息按规则写入 Excel。
*   **打包 (`core/packager.py`):**
    *   实现 `ReleasePackager` 类。
    *   根据配置定义打包结构（如创建 `MTK_{tag}` 目录）。
    *   收集 Patch 文件（根据 `GitRepoInfo` 中的记录）和 Commit Log（可能来自 Excel 或直接生成）。
    *   将文件按相对路径放入指定目录结构。
    *   使用 `shutil.make_archive` 创建压缩包。
*   **部署 (`core/deployer.py`):**
    *   引入传输库（如 `paramiko` for SFTP/SCP）。
    *   实现 `Deployer` 类，读取目标服务器配置。
    *   将生成的压缩包传输到指定位置。
*   **Jiri Snapshot:** 在适当的流程节点（可能是打标后或发布前）调用 `jiri snapshot` 命令（通过 `CommandExecutor`）。
*   **流程编排 (`release.py`):**
    *   取消同步和打标逻辑的注释，并确定打标操作的确切执行时机（构建前？构建后？两次？）。
    *   集成 Commit 分析、Patch 生成、报告、打包、部署等新模块的调用。
    *   添加命令行参数解析 (`argparse`)，以支持更灵活的调用（如指定 TAG、选择执行步骤、覆盖配置项）。
    *   实现手动/自动合并远端 MR 的选项（这可能需要与 Git 平台 API 集成，比较复杂）。
*   **配置完善:**
    *   为新功能添加对应的配置项和 Schema（如 `ReleaseConfig`, `AnalysisConfig`）。
    *   明确全局参数（TAG、描述、CR 等）的配置位置。

**6. 如何扩展 (How to Extend)**

*   **添加新仓库:** 在 `repos_config.py` 中添加新的 `RepoConfig` 实例。如果需要特殊同步，在 `sync_config.py` 中添加或修改策略。
*   **添加新构建类型:** 在 `BuildConfig` 中定义新的 `BuildTypeConfig`，并在 `BuildSystem` 中添加对应的 `build_xxx` 方法和 `_handle_xxx_git_operations` 方法。
*   **修改同步逻辑:** 编辑 `sync_config.py` 中对应策略的 `sync_actions`。
*   **修改打标逻辑:** 编辑 `Tagger` 类或 `tag_utils.py`。
*   **添加新命令类型:** 在 `CommandExecutor` 中添加新的 `execute_xxx_command` 方法。

