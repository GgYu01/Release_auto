
本项目是一个用于管理和维护多个软件仓库的自动化工具。它支持 Git、Jiri 和 Repo 三种类型的仓库，可以自动化分析仓库的提交、生成补丁以及其它仓库管理操作。

## 代码功能模块

### 1. `config/repos_config.py`

该文件定义了所有需要管理的仓库的配置信息。其中，核心配置为 `AllReposConfig` 类，它包含了每个仓库的 `RepoConfig` 对象。每个 `RepoConfig` 对象包括以下配置信息：

*   `repo_name`: 仓库名称
*   `repo_type`: 仓库类型（`git`, `jiri`, `repo`）
*   `path`: 仓库本地路径
*   `manifest_path`: `jiri` 或 `repo` 仓库的 manifest 文件路径
*   `manifest_type`: `jiri` 或 `repo`
*   `default_tag_prefix`: 标签前缀
*   `default_analyze_commit`: 是否默认分析提交
*   `default_generate_patch`: 是否默认生成补丁
*   `all_branches`: 所有分支（`jiri` or `repo`）
*   `special_branch_repos`: 分支特殊的仓库配置 （`jiri` or `repo`）

**示例配置项:**

*   `grpower_config`
*   `grt_config`
*   `grt_be_config`
*   `nebula_config`
*   `yocto_config`
*   `alps_config`

### 2. `config/schemas.py`

该文件定义了项目中所有的数据结构，主要包括以下三个类：

*   **`GitRepoInfo`**: 用于存储单个 Git 仓库的信息。

    *   `repo_name`: 仓库名称。
    *   `repo_parent`: 仓库所属的上级模块名称。
    *   `path`: 仓库的本地路径。
    *   `repo_type`: 仓库类型，固定为 "git"。
    *   `tag_prefix`: 标签前缀。
    *   `remote_name`: 远程仓库名称。
    *   `remote_branch`: 远程分支名称。
    *   `parent_repo`: 父仓库名称。
    *   `commit_analyses`: 提交分析结果列表。
    *   `newest_version`: 最新版本号。
    *   `next_newest_version`: 次新版本号。
    *   `analyze_commit`: 是否分析提交。
    *   `generate_patch`: 是否生成补丁。
    *   `branch_info`:  分支信息。
    *   `push_template`: 推送模板信息。
*   **`RepoConfig`**: 用于存储单个仓库（包括 Git、Jiri 和 Repo 类型的仓库）的配置信息。

    *   `repo_name`: 仓库名称。
    *   `repo_type`: 仓库类型（"git", "jiri", "repo"）。
    *   `path`: 仓库的本地路径。
    *   `git_repos`:  该仓库包含的 `GitRepoInfo` 列表。
    *   `manifest_path`: manifest 文件路径。
    *   `default_tag_prefix`: 默认的标签前缀。
    *   `parent_repo`: 父仓库名称。
    *   `manifest_type`: manifest 类型（"jiri", "repo"）。
    *   `default_analyze_commit`: 是否默认分析提交。
    *   `default_generate_patch`: 是否默认生成补丁。
    *   `all_branches`: 所有分支列表。
    *   `special_branch_repos`: 特殊分支的仓库配置字典。
*   **`AllReposConfig`**: 用于存储所有仓库的配置信息。

    *   `repo_configs`: 仓库配置字典，键为仓库名称，值为 `RepoConfig` 对象。
    *   `all_git_repos()`: 一个生成器函数，按顺序返回所有被管理的 `GitRepoInfo` 对象。

### 3. `core/repo_manager.py`

该文件定义了 `RepoManager` 类，用于管理仓库的初始化和解析 manifest 文件。

**`RepoManager` 类:**

*   `__init__(self, all_repos_config: AllReposConfig)`: 构造函数，接收 `AllReposConfig` 对象作为参数。
*   `parse_manifest(self, repo_config: RepoConfig)`: 解析 `jiri` 或 `repo` 的 manifest 文件，并将解析到的 Git 仓库信息添加到 `repo_config.git_repos` 中。
    *   `_parse_jiri_manifest(self, repo_config: RepoConfig)`: 解析 `jiri` 类型的 manifest 文件并获取 `GitRepoInfo` 信息。
    *   `_parse_repo_manifest(self, repo_config: RepoConfig)`: 解析 `repo` 类型的 manifest 文件并获取 `GitRepoInfo` 信息。
*   `initialize_git_repos(self)`: 初始化所有仓库的 Git 仓库信息。对于 `git` 类型的仓库，直接创建 `GitRepoInfo` 对象；对于 `jiri` 和 `repo` 类型的仓库，调用 `parse_manifest` 方法解析 manifest 文件。该函数还会调用 `RepoPropertyUpdater` 来更新所有仓库的属性信息。

### 4. `core/repo_updater.py`

该文件定义了 `RepoPropertyUpdater` 类，用于更新 Git 仓库的属性信息。

**`RepoPropertyUpdater` 类:**

*   `__init__(self, all_repos_config: AllReposConfig)`: 构造函数，接收 `AllReposConfig` 对象作为参数。
*   `_get_repo_config(self, parent_name: str) -> Optional[RepoConfig]`: 根据父仓库名称获取 `RepoConfig` 对象。
*   `_update_git_repo_properties(self, git_repo: GitRepoInfo, repo_config: RepoConfig) -> GitRepoInfo`: 更新单个 Git 仓库的属性信息，包括标签前缀、是否分析提交、是否生成补丁以及分支信息。
*   `update_all_repos(self) -> None`: 更新所有仓库的 Git 仓库属性信息。

### 5. `utils/file_utils.py`

该文件定义了 `construct_path` 函数，用于拼接路径。

**`construct_path` 函数:**

*   `construct_path(base_path, relative_path)`: 将 `base_path` 和 `relative_path` 拼接成一个完整的路径，并展开 `base_path` 中的用户目录。

### 6. `utils/rich_logger.py`

该文件定义了 `RichLogger` 类，用于提供美观的日志输出。

**`RichLogger` 类:**

*   `__init__(self, name, log_file="release.log")`: 构造函数，初始化日志记录器，设置日志级别、格式和输出方式（控制台和文件）。
*   `info(self, message, *args, **kwargs)`: 记录 INFO 级别的日志。
*   `warning(self, message, *args, **kwargs)`: 记录 WARNING 级别的日志。
*   `error(self, message, *args, **kwargs)`: 记录 ERROR 级别的日志。
*   `save_html(self, path='log.html')`: 将日志保存为 HTML 文件。

### 7. `release.py`

该文件是项目的入口文件。

**`main` 函数:**

1. 创建 `RepoManager` 对象，并传入 `all_repos_config`。
2. 调用 `repo_manager.initialize_git_repos()` 初始化所有仓库信息。
3. 遍历 all_repos_config 中所有 Git 仓库信息，并打印输出。
4. 保存日志到 HTML 文件。

## 总结

该项目实现了一个灵活的仓库管理工具，通过配置可以方便地管理不同类型的多个仓库。核心功能包括：

*   支持 Git, Jiri, Repo 仓库
*   可配置自动解析 manifest 文件
*   可配置 tag 前缀等属性
*   可配置默认的提交分析和补丁生成行为






请你把我;;;;;;之间的内容转换为专业全英文的prompt，我将把你的prompt用于指导其他的LLM生成代码，你并不需要生产任何代码，我只需要你提供prompt，所有的prompt要连续，不间断的放在一个代码块里，方便我查看。
;;;;;;
请使用简体中文回答、说明、介绍。
实际代码中的任何内容都必须全部是专业的英文。

我需要你基于我已有的功能完成新的功能
已有功能：
本项目是一个用于管理和维护多个软件仓库的自动化工具。它支持 Git、Jiri 和 Repo 三种类型的仓库，可以自动化分析仓库的提交、生成补丁以及其它仓库管理操作。

config/logging_config.py、config/repos_config.py、config/schemas.py、core/repo_manager.py、core/repo_updater.py、utils/file_utils.py、utils/rich_logger.py、utils/tag_utils.py

我需要你完成的新功能是：我希望能够通过一个 Python 配置文件来定义全局参数，例如要打的 TAG 版本标识、分支、描述信息、CR、title、commit message 格式、是否需要执行 nebula-sdk、nebula、TEE 的更新等，以便在 release 过程中使用这些参数。
所有实现的功能尽可能使用跨平台的库，而不是调用终端命令。
第一步，对于parent是alps 和 yocto 的仓库，需要依次执行：git fetch --all ,git checkout -f remotes/m/master,git reset --hard remotes/m/master,git clean -fdx这四步命令。对于parent是nebula的仓库，在nebula代码库的路径下执行mkdir -p ./.jiri_root/bin，rm -f .jiri_manifest .config .prebuilts_config，~/grpower/bin/jiri -j=2 import -remote-branch="master" "cci/nebula-main" ssh://gerrit:29418/manifest，~/grpower/bin/jiri -j=8 runp git checkout -f JIRI_HEAD --detach ，~/grpower/bin/jiri -j=2 update -gc -autoupdate=false -run-hooks=false --attempts=10 --force-autoupdate=true --rebase-all=false --rebase-tracked=false --rebase-untracked=false --show-progress=true --color=auto ,~/grpower/bin/jiri -j=8 runp "git remote get-url origin | sed 's/gerrit/gerrit-review/' | xargs git remote set-url --push origin" ，然后分析是否有特殊的子git仓库需要切换分支，若有则在对应子git仓库git checkout -f 特殊分支名，git reset --hard 远程特殊分支名 ，git pull即可。
对于parent是grpower 的仓库，执行git checkout -f 本地分支名 ，git reset --hard 远端分支名 和git pull。
对于parent是grt和grt_be的仓库，执行git checkout -f 本地分支名 ，git reset --hard 远端分支名 ，git clean -fdx和git pull。

当第一步sync基础环境做好后，我需要进行第二步：设计对所有全部子git仓库打tag的功能，tag全名按照本仓库的tag前缀+共同的版本标识，比如2025_0125_01，我只需要定义版本标识。
第三步，tag成功在本地打后，需要push到远端gerrit上面。

其他暂时无需做，第二步和第三步需要加enable和disable的开关，默认情况下只会打印类似  准备在 仓库名  绝对路径 commit id为多少 HEAD的commit message信息 打 拼接后的tag名的详细日志，后续实操执行不会默认执行，方便我调试。

我对代码的规范要求如下：
1. 代码采用高度模块化设计，支持后续扩展和维护。
2. 不考虑安全性、性能和资源占用，只注重可配置性和灵活性。
3. 功能尽量以Python库或第三方包实现，不使用Bash命令。
4. 使用完整的异常处理机制确保运行稳定。
5. 配置系统应全面、可独立管理，并能在不修改代码的情况下灵活控制功能。
6. 禁止在代码中包含注释或docstring。
7. 模块化结构需利用Python高级特性（装饰器、类、插件架构、扩展模块、上下文管理器、依赖注入等）。
8. 遵循最佳实践，确保代码清晰、简洁、健壮，且具备灵活的包结构。

;;;;;;
