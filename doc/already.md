**项目名称:** GR Release Automation Tool

**1. 项目概述与目标 (Project Overview & Goals)**

*   **核心目标:** 创建一个自动化的 Python 工具，用于管理涉及多个代码仓库（独立 Git、Jiri 管理、Repo 管理）的复杂发布流程。该流程包括代码同步、基于中心版本源的变更分析、构建（区分不同环境如 HEE/TEE）、版本标记（打 Tag）、变更分析、补丁生成、Excel 报告生成、产物打包和发布。
*   **解决痛点:** 取代原有参数硬编码、手动操作繁琐、易出错的 Bash 脚本，提高发布流程的效率、可靠性和可维护性。
*   **关键特性:**
    *   **多仓库统一管理:** 无缝处理不同类型（Git, Jiri, Repo）和来源的代码仓库。
    *   **配置驱动:** 通过 Python 配置文件集中管理仓库信息、构建参数、发布选项、分支策略、标签规则、合并策略、Patch 生成规则、Excel 报告规则、打包规则、部署目标等。
    *   **模块化设计:** 功能分离，易于理解、维护和扩展。
    *   **自动化流程:** 最小化人工干预，实现端到端的发布操作。
    *   **健壮性:** 包含详细日志、错误处理和状态反馈。
    *   **Gerrit 集成:** 支持通过配置自动或手动触发 Gerrit 代码评审的合并。
    *   **Excel 报告生成:** 能够根据分析结果自动生成结构化的 Excel Release Notes 文件。

**2. 设计理念 (Design Philosophy)**

*   **配置优于编码:** 尽可能将易变信息（路径、分支名、标签格式、开关、合并模式、版本源仓库、临时目录、包名模板、部署服务器、Excel 文件名、报告人等）放入配置文件，代码负责实现核心逻辑。
*   **显式优于隐式:** 配置项和代码逻辑应清晰表达意图，避免依赖模糊的约定或本地环境状态（如尽量不依赖本地未提交的修改）。
*   **关注点分离:** 将仓库管理、命令执行、同步、合并、构建、打标、分析、Patch 生成、打包、部署等功能解耦到独立的模块/类中。
*   **抽象与封装:** 底层操作（如 `git`, `jiri`, `repo`, 文件操作，SSH 命令）被封装在工具类中，上层逻辑调用这些抽象接口。
*   **可扩展性:** 方便添加新的仓库类型、同步策略、构建步骤、合并目标或发布目标。

**3. 系统架构 (System Architecture)**

该系统主要由以下几个核心组件构成：

*   **配置层 (`config/`)**:
    *   `schemas.py`: 定义所有配置项的数据结构 (Data Classes)，提供类型安全和默认值。
        *   `GitRepoInfo`: - 包含 `commit_details: List[Dict[str, str]]` 用于存储分析后的 Commit 信息（替代了旧的 `commit_analyses`）。
        *   `AllReposConfig`: - 包含 `version_source_repo_name: Optional[str]` 字段，用于指定哪个仓库的标签决定全局版本。
        *   `BuildConfig`: TEE 构建配置中 `vm_audio_cfg.pb.txt` 路径已修正。
        *   `ExcelConfig`: 定义 Excel 报告生成相关的配置项（开关、输出文件名、测试人员、MTK 序列号、Zircon/Garnet 仓库名等）。
        *   `AllReposConfig`: 添加 `excel_config: Optional[ExcelConfig]` 字段，用于集成 Excel 配置。
    *   `repos_config.py`: 定义所有代码仓库的元数据（路径、类型、分支、所属父仓库、合并配置等）。
        *   - `AllReposConfig` 实例现在包含 `version_source_repo_name="grt"`。
        *   - `grt` 仓库配置中 `default_analyze_commit=True`, `default_generate_patch=True`。
        *   - `grt_be` 仓库配置中 `default_analyze_commit=True`, `default_generate_patch=True` (*注意：grt_be 当前在 `all_repos_config` 中被注释*）。
        *   - 当前 `all_repos_config` 仅激活了 "grt" 和 "nebula" 两个仓库配置。
        *   `excel_config`: 定义了一个 `ExcelConfig` 的实例。
        *   `all_repos_config`: 将 `excel_config` 实例赋值给了 `AllReposConfig` 的 `excel_config` 字段。
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
    *   `merger.py` (`GerritMerger`)**: 负责处理 Gerrit 代码合并。根据 `MergeConfig` 配置（`auto`/`manual`），识别目标 Change-ID（直接提供或从 Commit Hash 解析），并通过 SSH (`gerrit review --submit`) 执行自动合并，或提示进行手动合并。依赖 `GitOperator` 获取远程 URL、Commit 消息，并使用 `CommandExecutor` 执行 SSH 命令。
    *   `builder.py` (`BuildSystem`): 负责执行具体的构建流程（nebula-sdk, nebula, TEE），包括环境准备、调用构建脚本/命令、文件操作和构建后的 Git 提交/推送。
    *   `tagger.py` (`Tagger`): 负责为仓库生成并应用 Git 标签，支持自动生成版本号（基于日期和序列）或使用手动指定的版本号。
    *   `git_tag_manager.py` (`GitTagFetcher`): 负责从 Git 仓库获取标签信息，特别是最新的和次新的标签，用于后续分析或版本确定。
    *   `commit_analyzer.py` (`CommitAnalyzer`): - 负责分析指定版本范围内的 Git Commit。
        *   接收全局的 `newest_version_identifier` 和 `next_newest_version_identifier`。
        *   遍历配置中 `analyze_commit=True` 的仓库。
        *   使用 `tag_utils.construct_tag` 结合仓库自身的 `tag_prefix` 和全局版本标识符，生成该仓库对应的 `start_ref` 和 `end_ref`。
        *   调用 `GitOperator.get_commits_between(start_ref, end_ref)` 获取 Commit 列表。
        *   将获取到的 Commit 详细信息（ID, Author, Message）存储在 `GitRepoInfo.commit_details` 列表中。
    *   `patch_generator.py` (`PatchGenerator`) :
        *   负责根据 `generate_patch=True` 的配置和 Commit 分析结果生成 Patch 文件。
        *   调用 `GitOperator.format_patch` 在临时目录中生成 patch。
        *   **关联 Patch 与 Commit**: 通过排序确保生成的 patch 文件（如 `0001-xxx.patch`）与 `CommitAnalyzer` 输出的有序 Commit 列表一一对应。
        *   计算并存储最终的相对路径 (`repo_parent/relative_path/patch_filename`) 到 `CommitDetail.patch_path`。
        *   **特殊 Commit 处理**: 识别来自特定源仓库（如 `grt`, `alps/.../grt`）且 Commit Message 包含特殊标记（`SPECIAL_PATTERNS`: TEE, nebula-sdk 等）的 Commit，并记录其 ID 与 Patch 路径的映射。（`special_commit_patch_map`）。
        *   ** * 修改 * Patch 路径映射**: 生成并返回一个 `patch_details_map` 字典，该字典将每个生成的 Patch 的最终相对路径 (arcname) 映射到其在临时目录中的绝对路径。这个映射将传递给 Packager 使用。
        *   **Nebula 链接**:
            *   根据 `release.py` 提供的映射关系，将 Nebula 子仓库 Commit 的 `patch_path` 指向其关联的特殊 Commit 的 Patch 路径（取第一个匹配）。
            *   根据所有关联的特殊 Commit 的 Message，推断并填充 Nebula 子仓库 Commit 的 `commit_module` 列表。
        *   提供临时 Patch 目录清理功能。
    *   `packager.py` (`ReleasePackager`):
        *   负责根据配置将分析结果（主要是 Patch 文件和 Excel 报告）打包成发布件。
        *   读取 `PackageConfig` 获取项目名和 ZIP 文件名模板。
        *   遍历 `all_repos_config` 中的 `GitRepoInfo`。
        *   Patch 文件定位: 基于临时目录结构和仓库名推断 Patch 源文件路径。而是接收由 `PatchGenerator` 生成并通过 `release.py` 传递的 `patch_details_map` (arcname -> absolute source path)，直接根据 `CommitDetail.patch_path` (arcname) 从映射中查找源文件的绝对路径。
        *   将 Patch 文件按照 `CommitDetail.patch_path` 定义的相对路径添加到 ZIP 压缩包中。
        *   : 接收 `excel_config` 和生成的 Excel 文件路径 (`generated_excel_path`)。如果 Excel 报告功能启用 (`excel_config.enabled`) 且文件已成功生成 (`generated_excel_path` 非空且存在)，则将该 Excel 文件（使用 `excel_config.output_filename` 作为在 ZIP 包内的名称）添加到压缩包中。
    *   `deployer.py` (`Deployer`):
        *   负责将打包好的发布件传输到目标服务器。
        *   读取 `DeployConfig` 获取 SCP 连接信息（主机、用户、路径、端口）。
        *   使用 `CommandExecutor` 执行 `scp` 命令上传 ZIP 文件。
    *   `reporter.py` (`ExcelReporter`): (位于 `utils/excel_utils.py`) 负责将 Commit 信息写入指定的 Excel 文件。
        *   读取 `ExcelConfig` 配置。
        *   如果配置启用，则尝试加载 `target_excel_path` 指定的现有 Excel 文件，或创建新文件。
        *   如果加载现有文件，会读取已有数据。
        *   使用 `GitOperator.get_latest_commit_id` 获取 Zircon 和 Garnet 仓库的最新 Commit ID（仓库名来自 `ExcelConfig`）。
        *   遍历 `all_repos_config` 中的 `CommitDetail`，为每个 commit 构建一行数据，包含版本号、Commit 消息、模块（优先取 `commit_module`，其次取 `repo_parent`）、Patch 路径、Zircon/Garnet Commit ID 字符串、测试人/作者/MTK Owner 字符串、当前日期、固定占位符列、Commit ID。
        *   将所有新生成的行数据插入到 Excel 表格的开头（第 2 行开始）。
        *   如果加载了旧数据，则将旧数据写回到新数据之后。
        *   保存 Excel 文件。
        *   包含详细的日志记录和错误处理（如文件无效、权限错误）。

*   **工具层 (`utils/`)**:
    *   `command_executor.py` (`CommandExecutor`): 统一执行外部命令（Shell, Git, Jiri, SSH等），提供日志记录和错误处理。
    *   `custom_logger.py` (`Logger`): 提供基于 Loguru 的日志记录功能。
    *   `file_utils.py` (`FileOperator`, `construct_path`): 封装文件和目录操作。
    *   `git_utils.py` (`GitOperator`): 封装常用的 Git 命令，提供更健壮的接口。
        *   `get_latest_commit_id`: 添加了一个新方法，用于获取指定仓库和分支（或 HEAD）的最新 Commit ID，供 `ExcelReporter` 使用。
    *   `tag_utils.py`: 提供版本标识符解析和生成的辅助函数。
    *   `excel_utils.py` (`ExcelReporter`): 封装了使用 `openpyxl` 库生成 Excel 报告的核心逻辑。

*   **入口 (`release.py`)**:
    *   应用程序的主入口点。
    *   负责解析命令行参数（*未来可能*）。
    *   初始化所有组件。


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
*   **Gerrit 变更合并 (`GerritMerger`)**:
    *   **配置驱动:** 每个仓库可以通过 `RepoConfig` 中的 `merge_config` (包含 `merge_mode`) 来控制合并行为 (`auto`, `manual`, `disabled`)。
    *   **目标识别:** 能够处理输入的标识符列表 (`commits_map`，**当前为空占位符**)。如果标识符是 Commit Hash，会尝试使用 `GitOperator.get_commit_message` 和 `utils.git_utils.extract_change_id` 来查找对应的 Change-ID。
    *   **自动合并 (`auto`模式):**
        *   使用 `GitOperator.get_remote_url` 获取仓库的远程 URL。
        *   使用 `utils.git_utils.parse_gerrit_remote_info` 解析出 Gerrit 服务器的主机、用户（可选）和端口（默认为 29418）。
        *   通过 `CommandExecutor` 执行 `ssh -p <port> <user>@<host> gerrit review --submit <change_id>` 命令来尝试自动合并。
    *   **手动合并 (`manual`模式):**
        *   记录清晰的日志信息，提示用户需要在 Gerrit 上手动合并指定的 Change-ID。
    *   **依赖关系:** 需要 `CommandExecutor` 执行命令，`GitOperator` 获取 Git 信息。
    *   **当前限制:** 依赖于外部提供的 `commits_map` 来确定要合并哪些变更，目前在 `release.py` 中使用空映射。
*   **模块化的构建系统 (`BuildSystem`):**
    *   区分 `nebula-sdk`, `nebula`, `TEE` 三种构建类型，逻辑分离在不同方法中。
    *   通过 `BuildConfig` 控制是否启用特定构建、构建前清理、构建后 Git 操作。
    *   封装了调用 `gr-nebula.py`, `gr-android.py`, `configure.sh`, `build_all.sh` 等外部脚本的逻辑。
    *   集成了 `FileOperator` 进行必要的文件复制（如 `zircon.elf`, `nebula*.bin`）和目录创建/清理。
    *   为每种构建类型实现了独立的 Git 操作（add, commit, push），使用不同的提交信息模板和目标分支/路径（定义在 `BuildGitConfig`）。
    *   构建环境（如 `PATH`, `SDK_APP_DIR` for `build_all.sh`）在执行命令时动态设置。
*   **版本标签管理:**
    *   `GitTagFetcher` 能够获取远程仓库的标签，过滤非合并到目标分支的标签，并基于创建日期和序列号 (`_NN`) 精确排序，找出最新和次新标签。
    *   `Tagger` 能够为所有配置的仓库打标签：
        *   支持通过 `TaggingConfig` 手动指定版本标识符 (`manual_version_identifier`)。
        *   若未手动指定，则自动生成 `YYYY_MMDD_NN` 格式的版本标识符，`NN` 基于当天已存在的标签自动递增。
        *   使用配置的时区 (`timezone`) 确定当前日期。
*   **中心化版本确定与 Commit 分析:**
    *   通过 `AllReposConfig.version_source_repo_name` 指定版本来源仓库。
    *   `release.py` 调用 `GitTagFetcher` 获取源仓库的最新/次新 Tag。
    *   `release.py` 使用 `tag_utils.extract_version_identifier` 提取全局版本标识符。
    *   `CommitAnalyzer` 使用全局标识符和各仓库的 `tag_prefix`（通过 `tag_utils.construct_tag`）来确定分析范围 (`start_ref..end_ref`)。
    *   `GitOperator.get_commits_between` 获取指定范围的 Commit 详细信息 (ID, Author, Message)。
    *   分析结果存储在 `GitRepoInfo.commit_details: List[Dict[str, str]]` 中。
*   **Patch 生成与处理 (`PatchGenerator`)**:
    *   **生成**: 对配置了 `generate_patch=True` 的仓库（排除 Nebula 子仓库和特定 Yocto 路径），使用 `GitOperator.format_patch` 在指定版本范围内生成 Patch 文件到临时目录 (`<temp_dir>/<parent_slug>/<repo_slug>/`)。
    *   **关联**: 按顺序将生成的 Patch 文件（如 `0001-xxx.patch`）与 `CommitAnalyzer` 提供的有序 Commit 列表关联。
    *   **路径存储**: 计算 Patch 在最终包内的相对路径 (`<parent>/<relative_path>/<patch_filename>`)，并存储在 `CommitDetail.patch_path` 中。
    *   **绝对路径映射**: **同时**，生成并返回一个 `patch_details_map` 字典，映射相对路径 (arcname) 到临时目录中的绝对路径，供打包器使用。
    *   **特殊识别**: 识别特定源仓库（`grt`, `alps/.../grt`）中 Message 包含特定模式 (`SPECIAL_PATTERNS`) 的 Commit，记录其 ID 和 Patch 路径映射 (`special_commit_patch_map`)。
    *   **Nebula 链接**:
        *   在 `release.py` 中，特殊 Commit 被识别并从源仓库的 `commit_details` 中移除。
        *   `PatchGenerator.link_nebula_patches` 使用映射关系 (`special_commit_patch_map`, `nebula_child_to_special_mapping`, `special_commit_messages`)，将 Nebula 子仓库 `CommitDetail` 的 `patch_path` 指向关联的（第一个匹配的）特殊 Commit 的 Patch 路径。
        *   根据所有关联的特殊 Commit Message，推断并填充 Nebula 子仓库 `CommitDetail` 的 `commit_module` 列表 (如 `['TEE']`, `['nebula-sdk']`)。
    *   **清理**: 提供清理临时 Patch 目录的功能。
*   ** * 新增 * Excel 报告生成 (`ExcelReporter` - `utils/excel_utils.py`)**:
    *   根据 `ExcelConfig` 中的 `enabled` 标志决定是否执行。
    *   读取 `ExcelConfig` 中定义的输出文件名 (`output_filename`)、测试人员 (`tester_name`)、MTK Owner (`mtk_owner_serial`)、Zircon/Garnet 仓库名 (`zircon_repo_name`, `garnet_repo_name`)。
    *   调用 `GitOperator.get_latest_commit_id` 获取 Zircon 和 Garnet 仓库的最新 Commit ID。
    *   遍历所有仓库的 `CommitDetail`。
    *   生成 Excel 行数据，包含版本号 (`version_info['latest_tag']`)、Commit 消息、模块、Patch 路径、Zircon/Garnet Commit 字符串、测试人/作者/MTK 字符串、当前日期等。
    *   使用 `openpyxl` 库操作 Excel 文件：
        *   如果目标文件存在且有效，加载它并读取现有数据。
        *   如果文件不存在或无效，则创建新文件并添加表头。
        *   将新生成的 Commit 数据行**插入**到表格的第 2 行开始。
        *   将之前读取的旧数据（如有）写回到新数据之后。
        *   保存文件。
*   **发布包生成 (`ReleasePackager`)**:
    *   根据 `PackageConfig` 中的模板生成 ZIP 文件名。
    *   遍历所有仓库的 `CommitDetail` 列表。
    *   Patch 定位: 使用传入的 `patch_details_map`，通过 `CommitDetail.patch_path` (作为 key) 查找 Patch 源文件的**绝对路径**。
    *   将找到的 Patch 文件按照 `CommitDetail.patch_path` 指定的路径添加到 ZIP 压缩包内。
    *   Excel 报告包含: 如果 `excel_config` 启用且 `generated_excel_path` 有效，则将该 Excel 文件添加到 ZIP 包的根目录（使用 `excel_config.output_filename` 作为文件名）。
*   **部署 (`Deployer`)**:
    *   读取 `DeployConfig` 中的 SCP 连接参数。
    *   使用 `CommandExecutor` 调用 `scp` 命令，将生成的 ZIP 包上传到指定的远程服务器路径。
*   **健壮的底层工具:**
    *   `CommandExecutor` 提供了统一的命令执行接口，包含详细的日志（执行命令、目录、成功/失败、输出预览/错误信息）。
    *   `GitOperator` 封装了 Git 命令，提高了易用性和可靠性（如处理 "nothing to commit" 的情况）。
    *   `FileOperator` 提供了带日志和错误处理的文件操作。
    *   `Logger` 提供统一、可配置的日志记录。
    *   `ExcelReporter`: 提供了带日志和错误处理的 Excel 文件生成功能。

**5. 未来工作 / 待实现功能 (Future Work / Missing Features)**

根据你的设计思路，以下功能是后续需要开发或完善的：

*   **Jiri Snapshot:** 在适当的流程节点（可能是打标后或发布前）调用 `jiri snapshot` 命令（通过 `CommandExecutor`）。
*   **流程编排 (`release.py`):**
    *   取消同步和打标逻辑的注释，并确定打标操作的确切执行时机（构建前？构建后？两次？）。
    *   集成 Commit 分析、Patch 生成、报告、打包、部署等新模块的调用。
    *   添加命令行参数解析 (`argparse`)，以支持更灵活的调用（如指定 TAG、选择执行步骤、覆盖配置项）。
*   **配置完善:**
    *   为新功能添加对应的配置项和 Schema（如 `ReleaseConfig`, `AnalysisConfig`）。
    *   明确 commits_map 的数据来源配置方式
    *   明确全局参数（TAG、描述、CR 等）的配置位置。

**6. 如何扩展 (How to Extend)**

*   **添加新仓库:** 在 `repos_config.py` 中添加新的 `RepoConfig` 实例。并按需配置其 merge_config。如果需要特殊同步，在 `sync_config.py` 中添加或修改策略。
*   **添加新构建类型:** 在 `BuildConfig` 中定义新的 `BuildTypeConfig`，并在 `BuildSystem` 中添加对应的 `build_xxx` 方法和 `_handle_xxx_git_operations` 方法。
*   **修改同步逻辑:** 编辑 `sync_config.py` 中对应策略的 `sync_actions`。
*   **修改打标逻辑:** 编辑 `Tagger` 类或 `tag_utils.py`。
*   **修改合并逻辑:** 编辑 `core/merger.py` (`GerritMerger`) 或相关的配置 (`MergeConfig`)。
*   **添加新命令类型:** 在 `CommandExecutor` 中添加新的 `execute_xxx_command` 方法。

