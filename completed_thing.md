
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






好的，请你把我;;;;;;之间的内容转换为专业全英文的prompt，我将把你的prompt用于指导其他的LLM生成代码，你并不需要生产任何代码，我只需要你提供prompt，所有的prompt要连续，不间断的放在一个代码块里，方便我查看。
;;;;;;
请使用简体中文回答、说明、介绍。
实际代码中的任何内容都必须全部是专业的英文。
我修改了日志记录方式，不再使用rich了。
我执行代码的输出信息如下，看起来我以前调用的日志记录方法，import的内容可能需要改变，请你做出对应的修改，谢谢。
nebula@ab2c1af07fa4:~/Release_auto $ python3 release.py 
Traceback (most recent call last):
  File "release.py", line 1, in <module>
    from config.repos_config import all_repos_config
  File "/home/nebula/Release_auto/config/repos_config.py", line 2, in <module>
    from utils.rich_logger import RichLogger
ImportError: cannot import name 'RichLogger' from 'utils.rich_logger' (/home/nebula/Release_auto/utils/rich_logger.py)

;;;;;;

请使用简体中文回答、说明、介绍。
实际代码中的任何内容都必须全部是专业的英文。
我请你修改utils/rich_logger.py，我不想在终端输出信息，所有信息不要输出到终端，而是记录在指定的日志文件里面，请保持日志文件格式、编码格式兼容Windows和linux，日志记录、写入必须改用Loguru实现。
我发现每行日志有类似两种不同输出行号的方式，我任务只需要一种，请你解决这个问题。
我对代码的规范要求如下：
1. 代码采用高度模块化设计，支持后续扩展和维护。
2. 不考虑安全性、性能和资源占用，只注重可配置性和灵活性。
3. 功能尽量以Python库或第三方包实现，不使用Bash命令。
4. 使用完整的异常处理机制确保运行稳定。
5. 配置系统应全面、可独立管理，并能在不修改代码的情况下灵活控制功能。
6. 禁止在代码中包含注释或docstring。
7. 模块化结构需利用Python高级特性（装饰器、类、插件架构、扩展模块、上下文管理器、依赖注入等）。
8. 遵循最佳实践，确保代码清晰、简洁、健壮，且具备灵活的包结构。

我发现实际日志中输出的所有行号信息都是utils/rich_logger.py中的行号，而不是实际代码中的行号，请修正这个错误。
请详细说明一共有多少种可以供我使用的在python中记录日志文件的库？分别是什么？