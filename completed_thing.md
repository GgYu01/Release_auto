请你把我;;;;;;之间的内容转换为专业全英文的prompt，我将把你的prompt用于指导其他的LLM生成代码，你并不需要生成任何代码，我只需要你提供prompt，所有的prompt放在一个代码块里，方便我查看。
;;;;;;
你的回答中介绍和说明请使用简体中文，代码中的任何内容都必须全部是专业的英文。

我有一个现成的代码项目，已经完成了初步设计，已经可以把不同类型代码库，通过manifest文件解析为独立的子git仓库集，然后按照开发者预期的分类情况，按照特性把一些信息填入每个仓库的数据结构记录的参数中，已有功能涉及的代码文件：config/logging_config.py、config/repos_config.py、config/schemas.py、core/repo_manager.py、core/repo_updater.py、utils/file_utils.py、utils/custom_logger.py、utils/tag_utils.py，你需要理解这些已有的文件设计后，在此基础上添加新的功能。

## 代码项目第二步功能详细设计规划

**核心目标:**  实现基于不同父级仓库类型，自动化同步和更新Git子仓库的功能。

**设计原则:**

1. 代码采用高度模块化设计，支持后续扩展和维护。
2. 不考虑安全性、性能和资源占用，只注重可配置性和灵活性。
3. 功能尽量以Python库或第三方包实现，不使用Bash命令。
4. 使用完整的异常处理机制确保运行稳定。
5. 配置系统应全面、可独立管理，并能在不修改代码的情况下灵活控制功能。
6. 禁止在代码中包含注释或docstring。
7. 模块化结构需利用Python高级特性（数据类、装饰器、类、插件架构、扩展模块、上下文管理器、依赖注入等）。
8. 遵循最佳实践，确保代码清晰、简洁、健壮，且具备灵活的包结构。

我需要你完成的新功能是,遍历所有已有的git子仓库数据结构，对于parent是alps 和 yocto 的仓库，需要依次执行：git fetch --all ,git checkout -f remotes/m/master,git reset --hard remotes/m/master,git clean -fdx这四步命令。对于parent是nebula的仓库，在nebula代码库的路径下执行mkdir -p ./.jiri_root/bin，rm -f .jiri_manifest .config .prebuilts_config，~/grpower/bin/jiri -j=2 import -remote-branch="master" "cci/nebula-main" ssh://gerrit:29418/manifest，~/grpower/bin/jiri -j=8 runp git checkout -f JIRI_HEAD --detach ，~/grpower/bin/jiri -j=2 update -gc -autoupdate=false -run-hooks=false --attempts=10 --force-autoupdate=true --rebase-all=false --rebase-tracked=false --rebase-untracked=false --show-progress=true --color=auto ,~/grpower/bin/jiri -j=8 runp "git remote get-url origin | sed 's/gerrit/gerrit-review/' | xargs git remote set-url --push origin" ，然后分析是否有特殊的子git仓库需要切换分支，若有则在对应子git仓库git checkout -f 特殊分支名，git reset --hard 远程特殊分支名 ，git pull即可。
对于parent是grpower 的仓库，执行git checkout -f 本地分支名 ，git reset --hard 远端分支名 和git pull。
对于parent是grt和grt_be的仓库，执行git checkout -f 本地分支名 ，git reset --hard 远端分支名 ，git clean -fdx和git pull。
所有实现的功能尽可能使用跨平台的库，而不是调用终端命令。

**模块化结构:**

为实现新功能，建议在现有项目结构基础上新增和调整以下模块:

*   **新增模块:**
    *   **`core/sync` 模块:** 专门负责仓库同步和更新功能。
        *   **`core/sync/repo_synchronizer.py`:**  核心同步协调器，负责根据配置和仓库类型调用相应的同步策略。
        *   **`core/sync/sync_strategies.py`:**  定义各种仓库类型同步策略的模块，每个策略类负责处理特定父级仓库类型的同步逻辑。
    *   **`utils/command_executor.py`:**  封装命令执行操作，提供统一的命令执行接口，方便后续替换底层实现 (例如从 `subprocess`  切换到更高级的库)。
    *   **`config/sync_config.py`:**  专门用于存放同步功能相关的配置，例如不同父级仓库类型对应的同步命令和参数。

*   **调整现有模块:**
    *   **`config/schemas.py`:**  扩展 `RepoConfig` 和 `GitRepoInfo` 数据类，以支持同步功能所需的配置参数，例如同步策略类型、特定分支信息等。
    *   **`config/repos_config.py`:**  在仓库配置中增加同步相关的配置项，例如指定仓库的同步策略类型。

**功能组件设计:**

1.  **同步配置 (`config/sync_config.py` 和 `config/schemas.py`)**

    *   **`SyncAction` 数据类 (在 `config/schemas.py`) :** 定义单个同步动作的结构，包含动作类型 (如 `git_command`, `jiri_command`, `mkdir`, `rm` 等)，以及动作参数 (例如 git 命令的具体参数，目录路径等)。
    *   **`SyncStrategyConfig` 数据类 (在 `config/schemas.py`) :**  定义同步策略的配置结构，包含策略名称，适用的父级仓库类型，以及同步动作列表 (`List[SyncAction]`)。
    *   **`AllSyncConfigs` 数据类 (在 `config/schemas.py`) :**  聚合所有同步策略配置 (`Dict[str, SyncStrategyConfig]`)。
    *   **`sync_strategies_config` 变量 (在 `config/sync_config.py`) :**  `AllSyncConfigs` 实例，静态配置不同父级仓库类型对应的同步策略和动作。配置内容应清晰地映射用户需求中的不同 parent 类型和对应的操作序列。

2.  **命令执行器 (`utils/command_executor.py`)**

    *   **`CommandExecutor` 类:**
        *   提供 `execute(self, command_type: str, command_params: Dict)` 方法，根据 `command_type` 调用不同的底层命令执行方法。
        *   支持的 `command_type` 包括:
            *   `git_command`: 执行 git 命令，参数为 git 命令和参数列表。
            *   `jiri_command`: 执行 jiri 命令，参数为 jiri 命令和参数列表。
            *   `mkdir`: 创建目录，参数为目录路径。
            *   `rm`: 删除文件或目录，参数为文件或目录路径。
        *   内部实现层面，初期可以使用 `subprocess` 模块执行 shell 命令。
        *   需要包含完善的异常处理，并记录命令执行日志。

3.  **同步策略 (`core/sync/sync_strategies.py`)**

    *   **`RepoSyncStrategy` 抽象基类:**
        *   定义 `sync(self, git_repo_info: GitRepoInfo, command_executor: CommandExecutor)` 抽象方法，接收 `GitRepoInfo` 对象和 `CommandExecutor` 实例作为输入，负责执行特定仓库的同步逻辑。
    *   **具体同步策略类 (继承自 `RepoSyncStrategy`):**
        *   `AlpsYoctoSyncStrategy`:  处理 `parent` 为 `alps` 和 `yocto` 的仓库同步。
        *   `NebulaSyncStrategy`:  处理 `parent` 为 `nebula` 的仓库同步，包含特殊的 jiri 命令和分支切换逻辑。
        *   `GrpowerSyncStrategy`:  处理 `parent` 为 `grpower` 的仓库同步。
        *   `GrtGrtBeSyncStrategy`:  处理 `parent` 为 `grt` 和 `grt_be` 的仓库同步。
        *   每个具体策略类在其 `sync` 方法中，根据 `SyncStrategyConfig` 配置的 `SyncAction` 列表，使用 `CommandExecutor` 执行相应的命令 sequence。
        *   `NebulaSyncStrategy` 需要特别处理用户需求中 "分析是否有特殊的子git仓库需要切换分支" 的逻辑。 这部分可以考虑在配置中预先定义需要特殊处理的子仓库列表和对应的分支信息，策略类根据配置进行判断和操作。

4.  **仓库同步器 (`core/sync/repo_synchronizer.py`)**

    *   **`RepoSynchronizer` 类:**
        *   依赖注入 `AllReposConfig` 和 `CommandExecutor` 实例。
        *   提供 `sync_repos(self)` 方法，作为同步功能的入口。
        *   `sync_repos` 方法的实现逻辑:
            1.  遍历 `all_repos_config.all_git_repos()` 获取所有 `GitRepoInfo` 对象。
            2.  根据 `git_repo_info.repo_parent`  判断仓库的父类型。
            3.  根据父类型选择相应的 `RepoSyncStrategy` 实例 (可以使用工厂模式或简单的条件判断)。
            4.  调用选定策略的 `sync(git_repo_info, command_executor)` 方法，执行仓库同步操作。
            5.  进行异常处理和日志记录。

5.  **集成到现有代码流程 (`release.py` 和 `core/repo_manager.py`)**

    *   在 `release.py` 中，在 `RepoManager` 初始化并完成仓库信息解析后，初始化 `CommandExecutor` 和 `RepoSynchronizer` 实例，并将 `AllReposConfig` 和 `CommandExecutor` 实例注入 `RepoSynchronizer`。
    *   在 `release.py` 的主流程中，调用 `RepoSynchronizer.sync_repos()` 方法，触发仓库同步功能。
    *   可能需要在 `core/repo_manager.py` 中扩展 `initialize_git_repos`  方法，在仓库信息初始化完成后立即进行同步操作，或者提供一个独立的同步入口点。

**配置示例 (示意性，`config/sync_config.py`):**

```python
from config.schemas import AllSyncConfigs, SyncStrategyConfig, SyncAction

sync_strategies_config = AllSyncConfigs(
    sync_configs={
        "alps_yocto_sync": SyncStrategyConfig(
            strategy_name="alps_yocto_sync",
            parent_types=["alps", "yocto"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "fetch", "args": ["--all"]}),
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "remotes/m/master"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "remotes/m/master"]}),
                SyncAction(action_type="git_command", action_params={"command": "clean", "args": ["-fdx"]}),
            ],
        ),
        "nebula_sync": SyncStrategyConfig(
            strategy_name="nebula_sync",
            parent_types=["nebula"],
            sync_actions=[
                SyncAction(action_type="mkdir", action_params={"path": "./.jiri_root/bin"}), # Path 需根据 GitRepoInfo 对象动态构建
                SyncAction(action_type="rm", action_params={"path": "./.jiri_manifest"}),  # Path 需根据 GitRepoInfo 对象动态构建
                SyncAction(action_type="rm", action_params={"path": ".config"}),        # Path 需根据 GitRepoInfo 对象动态构建
                SyncAction(action_type="rm", action_params={"path": ".prebuilts_config"}), # Path 需根据 GitRepoInfo 对象动态构建
                SyncAction(action_type="jiri_command", action_params={"command": "import", "args": ["-remote-branch=master", "cci/nebula-main", "ssh://gerrit:29418/manifest"]}), # jiri 命令参数需完整配置
                SyncAction(action_type="jiri_command", action_params={"command": "runp", "args": ["git", "checkout", "-f", "JIRI_HEAD", "--detach"]}),  # jiri 命令参数需完整配置
                SyncAction(action_type="jiri_command", action_params={"command": "update", "args": ["-gc", "-autoupdate=false", "-run-hooks=false", "--attempts=10", "--force-autoupdate=true", "--rebase-all=false", "--rebase-tracked=false", "--rebase-untracked=false", "--show-progress=true", "--color=auto"]}), # jiri 命令参数需完整配置
                SyncAction(action_type="jiri_command", action_params={"command": "runp", "args": ["git", "remote", "get-url", "origin", "|", "sed", "'s/gerrit/gerrit-review/'", "|", "xargs", "git", "remote", "set-url", "--push", "origin"]}), # jiri 命令参数需完整配置, 这里命令可能需要拆分或者特殊处理管道
                # 特殊分支处理逻辑可以在 NebulaSyncStrategy 类中实现，根据 GitRepoInfo.special_branch_repos 信息进行判断和 git checkout 操作
            ],
        ),
        "grpower_sync": SyncStrategyConfig(
            strategy_name="grpower_sync",
            parent_types=["grpower"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}), #  需要支持参数化配置，从 GitRepoInfo 中获取分支信息
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_branch}"]}), #  需要支持参数化配置，从 GitRepoInfo 中获取分支信息
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
        "grt_grt_be_sync": SyncStrategyConfig(
            strategy_name="grt_grt_be_sync",
            parent_types=["grt", "grt_be"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}), #  需要支持参数化配置，从 GitRepoInfo 中获取分支信息
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_branch}"]}), #  需要支持参数化配置，从 GitRepoInfo 中获取分支信息
                SyncAction(action_type="git_command", action_params={"command": "clean", "args": ["-fdx"]}),
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
    }
)
```
**总结:**

以上设计方案详细规划了如何为现有 Python 项目添加第二步功能，实现了高度模块化、可配置化和灵活性的仓库同步功能。  通过引入 `core/sync` 模块、`utils/command_executor.py` 和 `config/sync_config.py`  ，并结合策略模式和配置驱动的设计思想，满足了用户的所有需求，并为后续的功能扩展奠定了良好的基础。整个设计严格遵循了用户提出的所有代码规范和设计原则。

;;;;;;


请你把我;;;;;;之间的内容转换为专业全英文的prompt，我将把你的prompt用于指导其他的LLM生成代码，你并不需要生成任何代码，我只需要你提供prompt，所有的prompt放在一个代码块里，方便我查看。
;;;;;;
你的回答中介绍和说明请使用简体中文，代码中的任何内容都必须全部是专业的英文。

我有一个现成的代码项目，已经完成了初步设计，已经可以把不同类型代码库，通过manifest文件解析为独立的子git仓库集，然后按照开发者预期的分类情况，按照特性把一些信息填入每个仓库的数据结构记录的参数中，已有功能涉及的代码文件：config/logging_config.py、config/repos_config.py、config/schemas.py、core/repo_manager.py、core/repo_updater.py、utils/file_utils.py、utils/rich_logger.py、utils/tag_utils.py，你需要理解这些已有的文件设计后，在此基础上添加新的功能。

我需要你完成的新功能是,遍历所有已有的git子仓库数据结构，对于parent是alps 和 yocto 的仓库，需要依次执行：git fetch --all ,git checkout -f remotes/m/master,git reset --hard remotes/m/master,git clean -fdx这四步命令。对于parent是nebula的仓库，在nebula代码库的路径下执行mkdir -p ./.jiri_root/bin，rm -f .jiri_manifest .config .prebuilts_config，~/grpower/bin/jiri -j=2 import -remote-branch="master" "cci/nebula-main" ssh://gerrit:29418/manifest，~/grpower/bin/jiri -j=8 runp git checkout -f JIRI_HEAD --detach ，~/grpower/bin/jiri -j=2 update -gc -autoupdate=false -run-hooks=false --attempts=10 --force-autoupdate=true --rebase-all=false --rebase-tracked=false --rebase-untracked=false --show-progress=true --color=auto ,~/grpower/bin/jiri -j=8 runp "git remote get-url origin | sed 's/gerrit/gerrit-review/' | xargs git remote set-url --push origin" ，然后分析是否有特殊的子git仓库需要切换分支，若有则在对应子git仓库git checkout -f 特殊分支名，git reset --hard 远程特殊分支名 ，git pull即可。
对于parent是grpower 的仓库，执行git checkout -f 本地分支名 ，git reset --hard 远端分支名 和git pull。
对于parent是grt和grt_be的仓库，执行git checkout -f 本地分支名 ，git reset --hard 远端分支名 ，git clean -fdx和git pull。
所有实现的功能尽可能使用跨平台的库，而不是调用终端命令。

我对代码的规范要求如下：
1. 代码采用高度模块化设计，支持后续扩展和维护。
2. 不考虑安全性、性能和资源占用，只注重可配置性和灵活性。
3. 功能尽量以Python库或第三方包实现，不使用Bash命令。
4. 使用完整的异常处理机制确保运行稳定。
5. 配置系统应全面、可独立管理，并能在不修改代码的情况下灵活控制功能。
6. 禁止在代码中包含注释或docstring。
7. 模块化结构需利用Python高级特性（数据类、装饰器、类、插件架构、扩展模块、上下文管理器、依赖注入等）。
8. 遵循最佳实践，确保代码清晰、简洁、健壮，且具备灵活的包结构。

;;;;;;


我希望能够通过一个 Python 配置文件来定义全局参数，例如要打的 TAG 版本标识、分支、描述信息、CR、title、commit message 格式、是否需要执行 nebula-sdk、nebula、TEE 的更新等，以便在 release 过程中使用这些参数。


当第一步sync基础环境做好后，我需要进行第二步：设计对所有全部子git仓库打tag的功能，tag全名按照本仓库的tag前缀+共同的版本标识，比如2025_0125_01，我只需要定义版本标识。
第三步，tag成功在本地打后，需要push到远端gerrit上面。

其他暂时无需做，第二步和第三步需要加enable和disable的开关，默认情况下只会打印类似  准备在 仓库名  绝对路径 commit id为多少 HEAD的commit message信息 打 拼接后的tag名的详细日志，后续实操执行不会默认执行，方便我调试。
