

## **项目名称：** GR Release Automation Tool (暂定名)

**(文档版本: 0.2)**

### **1. 项目概述**

本文档旨在详细描述 "GR Release Automation Tool" 的设计与逻辑。该工具旨在自动化处理多个代码仓库（包括纯 Git 仓库以及通过 Jiri 和 Repo 管理的仓库集合）的发布流程，包括代码同步、版本管理（TAG 生成与分析）、选择性编译与推送、发布物打包（含 Commit 信息、Patch 文件、Excel 报告）等环节。其核心目标是提高发布效率、减少手动错误，并统一管理不同类型的代码仓库。

### **2. 核心组件与数据结构**

*   **配置管理 (`config/`):**
    *   使用 Python Dataclasses (`schemas.py`) 定义所有配置信息，包括仓库信息 (`RepoConfig`, `GitRepoInfo`)、同步策略 (`SyncStrategyConfig`)、构建配置 (`BuildConfig`)、TAG 生成规则 (`TaggingConfig`)、打包 (`PackageConfig`)、部署 (`DeployConfig`)、Excel报告 (`ExcelConfig`) 和日志 (`LoggingConfig`)。
    *   集中管理所有仓库（Git, Jiri-managed, Repo-managed）的元数据，如路径、远程地址、分支、TAG 前缀、是否需要分析/生成Patch等。
    *   允许定义不同仓库类型的同步策略 (`sync_config.py`)。
    *   配置文件（如 `repos_config.py`）提供具体的配置实例。
*   **仓库信息 (`GitRepoInfo`):** 这是核心的数据结构，用于统一表示一个独立的 Git 仓库，无论其父仓库是纯 Git、Jiri 管理还是 Repo 管理。
    *   **配置来源字段:** `repo_name`, `repo_parent`, `path`, `repo_path`, `repo_type`, `tag_prefix`, `remote_name`, `local_branch`, `remote_branch`, `parent_repo`, `relative_path_in_parent`, `analyze_commit`, `generate_patch`, `special_branch_repos`, `merge_config`, `push_template` (这些值主要来自 `repos_config.py` 或通过解析 Manifest 文件并结合 `RepoConfig` 的默认值获得)。
    *   **运行时获取字段:** `commit_details` (由 `CommitAnalyzer` 填充), `newest_version`, `next_newest_version` (由 `GitTagFetcher` 填充)。
*   **命令执行器 (`utils/command_executor.py:CommandExecutor`):** 负责执行所有外部命令（如 `git`, `jiri`, `repo`, `scp`, 编译命令等）的底层模块。提供统一接口，处理命令参数、工作目录、环境变量，并进行日志记录和基本的错误处理。
*   **Git 操作封装 (`utils/git_utils.py:GitOperator`):** 基于 `CommandExecutor`，封装了常用的 Git 操作，如 `fetch`, `checkout`, `reset`, `tag`, `log`, `format-patch`, `get_commits_between`, `push_to_remote` 等。提供更高级、面向任务的 Git 功能接口。
*   **日志系统 (`utils/custom_logger.py:Logger`):** 基于 `loguru`，提供统一的日志记录功能，支持按模块记录、配置日志级别、格式、轮转等。
*   **文件操作 (`utils/file_utils.py:FileOperator`):** 封装常用的文件/目录操作，如创建、删除、复制。

### **3. 详细工作流程**

#### **步骤 1: 配置加载与初始化**

*   **目的:** 读取预定义的配置，为后续所有操作准备好统一的、结构化的数据。
*   **逻辑说明:**
    1.  加载 `config/` 目录下的配置信息，特别是 `repos_config.py` 中定义的 `AllReposConfig` 实例。
    2.  `AllReposConfig` 包含所有顶级仓库 (`RepoConfig`) 的配置。
    3.  **仓库管理器 (`core/repo_manager.py:RepoManager`)** 负责初始化 `GitRepoInfo` 实例。
    4.  对于 `repo_type` 为 "git" 的 `RepoConfig`，直接为其创建一个 `GitRepoInfo`。
    5.  对于 `repo_type` 为 "jiri" 或 "repo" 的 `RepoConfig`，解析其 Manifest XML 文件，为 Manifest 中的**每一个 project** 创建一个对应的 `GitRepoInfo` 实例，并记录其 `repo_parent` 为父 `RepoConfig` 的名称。计算并存储 `repo_path` 和 `relative_path_in_parent`。
    6.  **属性更新器 (`core/repo_updater.py:RepoPropertyUpdater`)** 随后运行，确保所有 `GitRepoInfo` 都从其父 `RepoConfig` 继承了必要的默认配置（如 `tag_prefix`, `analyze_commit`, `generate_patch`, 分支信息等），除非被 `special_branch_repos` 或 Manifest 中的设置覆盖。
    7.  最终产出包含所有待处理 Git 仓库详细信息的 `AllReposConfig` 对象，供后续步骤使用。
*   **关键组件:** `config/schemas.py`, `config/repos_config.py`, `core/repo_manager.py`, `core/repo_updater.py`

#### **步骤 2: 初始化仓库信息数据结构**

*   **目的:** 确保所有需要操作的仓库信息都已结构化并加载到内存中。
*   **逻辑说明:** 这是步骤 1 的结果。此时 `all_repos_config` 对象已包含所有仓库的 `GitRepoInfo` 列表，其中大部分字段来自配置，而 `commit_details`, `newest_version`, `next_newest_version` 等字段将在后续流程中被填充。

#### **步骤 3: 代码同步与更新**

*   **目的:** 根据配置中指定的分支，将所有相关 Git 仓库的代码更新到最新状态。
*   **逻辑说明:**
    1.  **仓库同步器 (`core/sync/repo_synchronizer.py:RepoSynchronizer`)** 遍历所有 `GitRepoInfo`。
    2.  根据每个 `GitRepoInfo` 的 `repo_parent` 找到对应的同步策略 (`sync_strategy`) 名称。
    3.  从 `config/sync_config.py` 获取该策略定义的 `SyncAction` 列表。
    4.  **动作执行器 (`core/sync/action_executor.py:ActionExecutor`)** 依次执行每个 `SyncAction`：
        *   解析动作类型和参数。
        *   替换 Git 命令参数中的占位符 (`{local_branch}`, `{remote_name}`, `{remote_branch}`) 为 `GitRepoInfo` 中的实际值。
        *   调用 `CommandExecutor` 执行实际命令（如 `git fetch`, `git checkout`, `git reset`, `git pull` 等）。
*   **关键组件:** `core/sync/repo_synchronizer.py`, `core/sync/action_executor.py`, `config/sync_config.py`, `config/schemas.py` (Sync related), `utils/command_executor.py`

#### **步骤 4: 生成新 TAG 并对 Nebula/Grpower 子仓库打 TAG**

*   **目的:** 基于指定源仓库的最新 TAG，自动计算出本次发布的新版本 TAG，并将其应用到所有 Nebula 和 Grpower 管理下的 Git 子仓库。
*   **逻辑说明:**
    1.  **确定 TAG 生成源:** 找到 `all_repos_config.version_source_repo_name` (如 "grt") 对应的 `GitRepoInfo`。
    2.  **获取源仓库最新 TAG:**
        *   使用 **TAG 获取器 (`core/git_tag_manager.py:GitTagFetcher`)** 的 `fetch_latest_tags` 方法，针对此源仓库。
        *   `GitTagFetcher` 内部执行 `git fetch --tags`, `git tag --merged <branch>`, `git for-each-ref --sort=-creatordate --format='%(refname:strip=2) %(creatordate:iso-strict)'` 等命令。
        *   过滤掉不符合 `tag_prefix` 的 TAG。
        *   根据**创建日期 (主要)** 和 TAG 名称末尾的 **`_NN` 序列号 (次要)** 进行精确排序，找到时间上最新的那个 TAG。
    3.  **生成新版本标识符:**
        *   **提取:** 使用 `utils/tag_utils.extract_version_identifier` 从上一步获取的最新 TAG 中提取版本标识符 (`YYYY_MMDD_NN`)。
        *   **解析:** 使用 `utils/tag_utils.parse_version_identifier` 解析标识符，得到日期 (`tag_date`) 和计数器 (`counter`)。
        *   **获取当前日期:** 使用 `Tagger.get_current_time_in_config_timezone` 获取配置时区的当前时间。
        *   **查找当天最大序列号:** 检查源仓库中所有符合 `tag_prefix` 且日期部分与**当前日期** (`YYYY_MMDD`) 相同的 TAG，找出其中最大的 `NN` 序列号 (`Tagger._find_latest_sequence_number`)。
        *   **生成新标识符:** 使用 `utils/tag_utils.generate_next_version_identifier` 生成新标识符。逻辑为：如果当前日期与最新 TAG 日期相同，则序列号 `NN` 加 1；如果当前日期晚于最新 TAG 日期，则使用当前日期，序列号 `NN` 从 `01` 开始。
    4.  **构造新 TAG 名称:** 使用 `utils/tag_utils.construct_tag` 将**源仓库**的 `tag_prefix` 和新生成的版本标识符组合成完整的新 TAG 名称 (例如: `release-spm.mt8678_2024_0721_01`)。此 TAG 名称将被用于所有需要打 TAG 的仓库。
    5.  **应用 TAG:**
        *   遍历 `all_repos_config` 中所有的 `GitRepoInfo` 实例。
        *   筛选出 `repo_parent` 为 "nebula" 或 "grpower" 的所有 `GitRepoInfo`。
        *   对筛选出的**每一个子 Git 仓库** (`GitRepoInfo`)，使用 `GitOperator.tag` 方法，将上一步构造出的**同一个**新 TAG 名称打到它们当前的 HEAD commit 上。
*   **关键组件:** `core/git_tag_manager.py`, `utils/tag_utils.py`, `utils/git_utils.py:GitOperator`, `config/schemas.py` (`AllReposConfig.version_source_repo_name`), `config/tagging_config.py`, `core/tagger.py` (提供了部分逻辑实现)

#### **步骤 5: (可选) 执行编译与推送**

*   **目的:** 根据配置编译 nebula-sdk, nebula, TEE，生成二进制文件，并将结果 Commit 和 Push 到对应的仓库，准备进行 Gerrit 合入。
*   **逻辑说明:**
    1.  **构建系统 (`core/builder.py:BuildSystem`)** 负责此步骤。
    2.  检查 `BuildConfig` 中各构建类型的 `enabled` 标志。
    3.  执行环境清理（如果 `enable_environment_cleanup` 为 True）。
    4.  按顺序（nebula-sdk -> nebula -> TEE）执行启用的构建：
        *   执行预定义的编译命令，可能需要先运行脚本获取环境变量 (`_get_environment_after_sourcing` / `_get_environment_after_script_execution`)。
        *   使用 `FileOperator` 进行必要的文件操作（复制、链接等）。
        *   **Git 操作 (如果 `post_build_git` 为 True):**
            *   使用 `GitOperator.safe_add` 将生成或修改的文件添加到暂存区。
            *   使用 `GitOperator.commit_with_author` 生成本地 Commit，Commit Message 来自 `BuildConfig.git`。
            *   **使用 `GitOperator.push_to_remote` 将本地 Commit 推送到远程 Gerrit。** 推送目标由 `BuildConfig.git.remote_name`, `BuildConfig.git.remote_branch_xxx` 和 `BuildConfig.git.push_template` (例如 `HEAD:refs/for/<remote_branch>`) 共同决定。
*   **关键组件:** `core/builder.py`, `config/schemas.py` (Build related), `utils/command_executor.py`, `utils/file_utils.py`, `utils/git_utils.py` (包括 `push_to_remote`)

#### **步骤 6: 等待手动 Gerrit 合入**

*   **目的:** 暂停脚本执行，等待用户在 Gerrit 网页上手动审查并合入步骤 5 中推送的变更。
*   **逻辑说明:**
    1.  脚本打印提示信息，指示用户进行手动 Gerrit 合入操作。
    2.  通过 `input()` 等待用户按回车键确认操作完成。
    3.  `core/merger.py:GerritMerger` 存在，包含未来可能实现的自动合并逻辑（通过 SSH 调用 `gerrit review --submit`），但当前流程依赖手动操作。
*   **关键组件:** `release.py` (主流程控制), `core/merger.py` (潜在的自动合并逻辑)

#### **步骤 7: 对剩余仓库打 TAG**

*   **目的:** 将步骤 4 中生成的同一个新 TAG 应用到所有**未在步骤 4 中处理**的 Git 仓库（及其子仓库）。
*   **逻辑说明:**
    1.  脚本从步骤 6 恢复。
    2.  遍历 `all_repos_config` 中的所有 `GitRepoInfo` 实例。
    3.  筛选出 `repo_parent` **不**是 "nebula" 且 **不**是 "grpower" 的所有 `GitRepoInfo` (例如，来自 grt, grt_be, alps, yocto 等父仓库的 Git 仓库)。
    4.  对筛选出的**每一个 Git 仓库**，使用 `GitOperator.tag` 方法，将步骤 4 中生成的**同一个**新 TAG 名称打到它们当前的 HEAD commit 上。
*   **关键组件:** `release.py` (主流程控制), `utils/git_utils.py:GitOperator`

#### **步骤 8: 获取最新和次新 TAG (用于分析)**

*   **目的:** 从指定的源仓库获取最新的两个 TAG，确定 Commit 分析和 Patch 生成的时间范围。
*   **逻辑说明:**
    1.  再次针对 `version_source_repo_name` 指定的源仓库。
    2.  调用 `GitTagFetcher.fetch_latest_tags` 方法。
    3.  由于步骤 4/7 已完成打 TAG，此次调用会返回：
        *   **最新 TAG:** 步骤 4/7 中刚刚生成并应用的 TAG。
        *   **次新 TAG:** 本次流程开始前的那个最新 TAG。
    4.  `GitTagFetcher` 依然使用日期+序列号的健壮排序确保准确性。
    5.  存储这两个 TAG 名称用于下一步。
*   **关键组件:** `core/git_tag_manager.py`, `config/schemas.py` (`AllReposConfig.version_source_repo_name`)

#### **步骤 9: 分析、生成 Patch、处理 Nebula 映射、写 Excel、打包发布**

*   **目的:** 分析两个 TAG 之间的代码变更，生成 Patch 文件，处理 Nebula 仓库特殊的 Commit 映射关系，生成 Excel 报告，并将所有产出物打包成一个发布压缩包。
*   **逻辑说明:**
    1.  **提取版本标识符:** 从步骤 8 的两个 TAG 中提取版本标识符 (`newest_id`, `next_newest_id`)。
    2.  **Commit 分析 (`CommitAnalyzer.analyze_all_repositories`):**
        *   遍历所有 `analyze_commit=True` 的 `GitRepoInfo`。
        *   使用仓库各自的 `tag_prefix` 和全局的 `newest_id`, `next_newest_id` 构造 `start_ref` 和 `end_ref`。
        *   调用 `GitOperator.get_commits_between` 获取 Commit 列表，存入 `GitRepoInfo.commit_details`。
    3.  **特殊源仓库识别 (`release.py`):** 识别包含特殊 Commit 的源仓库列表 (`special_source_repo_infos`)。
    4.  **Patch 生成 (`PatchGenerator.generate_patches`):**
        *   遍历所有 `generate_patch=True` 的仓库（排除 nebula 子仓库和特定项）。
        *   使用对应的 `start_ref`, `end_ref` 调用 `GitOperator.format_patch` 生成 patch 文件到临时目录。
        *   按顺序关联生成的 Patch 和 `commit_details`，计算相对路径存入 `CommitDetail.patch_path`。
        *   构建 `patch_details_map` (`{相对路径: 绝对临时路径}`)。
        *   识别来源特殊且 Message 含特定标记的 Commit，存入 `special_commit_patch_map` (`{CommitID: 相对路径}`)。
    5.  **Nebula 映射处理 (`release.py:_process_nebula_mappings` & `PatchGenerator.link_nebula_patches`):**
        *   `_process_nebula_mappings`: 找出所有特殊 Commit ID (`special_commit_ids`) 及其 Message (`special_commit_messages`)。构建映射 `nebula_child_to_special_map` (`{NebulaCommitID: [所有SpecialCommitIDs]}`)。从源仓库移除这些特殊 Commit。*(确认逻辑：一个 Nebula Commit 关联所有特殊 Commit)*。
        *   `link_nebula_patches`: 遍历 Nebula 子仓库 Commit。查找其对应的 `special_commit_ids`。在 `special_commit_patch_map` 中查找这些 ID 的 Patch 路径，将**第一个**找到的路径赋给 Nebula Commit 的 `patch_path`。检查这些 ID 对应的 Message，如果含特殊标记，将模块名加入 Nebula Commit 的 `commit_module`。
    6.  **生成 Excel 报告 (`ExcelReporter.generate_report`):**
        *   如果启用，创建或加载 Excel。
        *   获取 Zircon/Garnet 最新 Commit ID。
        *   遍历所有仓库的 `commit_details`，提取信息，结合配置，生成新行数据。
        *   将新行**插入**到 Excel 表格顶部。
        *   保存 Excel 文件。
    7.  **打包发布物 (`ReleasePackager.package_release`):**
        *   创建 ZIP 文件。
        *   遍历 `commit_details`，对有 `patch_path` 的 Commit，使用 `patch_details_map` 找到源 Patch 文件，添加到 ZIP 中（使用相对路径）。
        *   如果 Excel 生成成功，将其添加到 ZIP。
        *   保存 ZIP 文件。
    8.  **(可选) 部署 (`Deployer.deploy_package`):** 如果配置，使用 `scp` 将 ZIP 包传输到目标服务器。
    9.  **清理 (`PatchGenerator.cleanup_temp_patches`):** 删除临时 Patch 目录。
*   **关键组件:** `release.py` (主流程), `core/commit_analyzer.py`, `core/patch_generator.py`, `utils/excel_utils.py`, `core/packager.py`, `core/deployer.py`, `utils/tag_utils.py`, `utils/git_utils.py`, `config/schemas.py`, `utils/command_executor.py`

### **4. 需要改进的点 (Refactoring / Future Improvements)**

*   **编译后 Git Push:** 当前 `BuildSystem` 的 `_handle_*_git_operations` 方法执行 `git add` 和 `git commit`。应在此之后增加 `git push` 操作 (调用 `GitOperator.push_to_remote`)，使用 `BuildConfig.git` 中定义的远程、分支和推送模板，确保编译产物在手动合并步骤之前推送到 Gerrit。 (当前代码已有 `push_to_remote` 方法，需确认 `BuildSystem` 是否调用它)。
*   **解耦 `release.py`:** `release.py` 中包含了一些具体的逻辑判断（如识别特殊源仓库、协调 Nebula 映射过程）。为了更好的模块化和可维护性，应将这些逻辑移入 `core` 目录下的相应模块或新的辅助类/函数中。`release.py` 应专注于调用核心组件的高级方法，传递必要的配置和状态信息，编排整体流程。

