
请根据我的需求给出对应的代码，你可以适当修改文件名、路径、创建文件、删除文件。

**代码整体要求：**

1. **高度模块化：** 代码必须采用高度模块化的设计，以便于后续的扩展和维护。
2. **仅关注配置性和灵活性：** 不考虑安全性、性能和资源消耗，只专注于代码的可配置性和灵活性。
3. **优先使用 Python 库：** 尽可能使用 Python 库或第三方包来实现功能，避免使用 Bash 命令。
4. **完善的异常处理：** 采用完整的异常处理机制，确保代码稳定运行。
5. **独立且灵活的配置系统：** 配置系统必须全面、可独立管理，并且足够灵活，无需修改代码即可控制功能。
6. **无注释：** 代码中禁止包含任何形式的注释或文档字符串 (docstring)。
7. **利用 Python 高级特性：** 模块化结构需要充分利用 Python 的高级特性，如装饰器、类、插件架构、扩展模块、上下文管理器、依赖注入等。
8. **遵循最佳实践：** 遵循最佳实践，确保代码清晰、简洁、健壮，并且具有灵活的包结构。
9. **丰富的日志输出：** 代码应支持跟踪和丰富的消息输出，日志部分应使用 rich logging 库进行详细记录。

**代码库信息定义与管理：**

*   **配置方式：** 使用 Python 文件和数据结构定义所有代码仓库的信息，禁止使用 JSON、YAML 等其他配置文件格式。要求直接使用 Python 代码文件定义配置，不能使用任何其他格式的配置文件。
*   **仓库信息：** 需要能够定义每个代码仓库的信息，包括：
    *   仓库名称 (repo\_name)
    *   仓库类型 (repo\_type)：包括 `git`、`jiri` 和 `repo` 三种类型。
    *   仓库路径 (path)
    *   标签前缀 (tag\_prefix)
    *   远程仓库名称 (remote\_name)
    *   远程分支名 (remote\_branch)
*   **具体仓库定义：**
    *   `grpower`：git 仓库，路径为 `~/grpower`
    *   `grt`：git 仓库，路径为 `~/grt`
    *   `grt_be`：git 仓库，路径为 `~/grt_be`
    *   `nebula`：jiri 仓库，路径为 `~/grpower/workspace/nebula`
    *   `yocto`：repo 仓库，路径为 `~/yocto`
    *   `alps`：repo 仓库，路径为 `~/alps`
*   **特殊处理 jiri 和 repo 仓库：**
    *   需要解析 jiri 和 repo 仓库的 manifest 文件。
    *   将 jiri 和 repo 仓库视为多个独立 git 仓库的集合。
    *   完全抛弃原生的 jiri 和 repo 工具。
*   **manifest 文件示例：**
    *   **repo manifest 示例：**

        ```xml
        <?xml version="1.0" encoding="UTF-8"?>
        <manifest>
          <remote fetch=".." name="grt-mt8678" review="https://www.goldenriver.com.cn:3443"/>
          <project name="yocto/src/connectivity/gps/4.0" path="src/connectivity/gps/4.0"/>
          <project name="yocto/src/tinysys/common" path="src/tinysys/common"/>
        </manifest>
        ```
    *   **jiri manifest 示例：**

        ```xml
        <manifest version="1.1">
          <projects>
            <project name="build" path="build" remote="ssh://gerrit:29418/build" remotebranch="nebula" gerrithost="http://gerrit" githooks="manifest/git-hooks"/>
            <project name="docs" path="docs" remote="ssh://gerrit:29418/docs" remotebranch="nebula" gerrithost="http://gerrit" githooks="manifest/git-hooks" />
        </manifest>
        ```

**数据结构设计：**

需要创建以下三个核心数据结构，用于存储和管理仓库信息：

1. **GitRepoInfo:** 用于存储单个 Git 仓库的详细信息，包括以下字段：
    *   `repo_name` (字符串): Git 仓库名称。例如 `yocto/src/connectivity/gps/4.0` 或 `grpower`。
    *   `repo_parent` (字符串): Git 仓库的父仓库, 与 RepoConfig 部分的定义一致。
    *   `path` (字符串): Git 仓库的本地路径。例如 `~/grpower` 或 `~/grpower/workspace/nebula/build`。
    *   `repo_type` (字符串): 仓库类型，例如 `git`、`jiri`、`repo`。
    *   `tag_prefix` (字符串): 此 Git 仓库使用的标签前缀。
    *   `remote_name` (字符串): 远程仓库的名称。例如 `grt-mt8678`。
    *   `remote_branch` (字符串): 远程分支的名称。例如 `nebula`。
    *   `parent_repo` (字符串): 指向此 Git 仓库的 RepoConfig 名称 (例如 `yocto`、`nebula`)。用于例如知道 Git 仓库的路径，可以回溯 `repo_type`。
    *   `commit_analyses` (列表): 用于存储 Git 仓库的提交分析结果。每个分析是一个字典，包含以下键：
        *   `commit_id` (字符串): 提交的 SHA-1 哈希值。
        *   `message` (字符串): 提交消息。
        *   `patch_file` (字符串): 由 `format-patch` 生成的补丁文件的路径。
        *   `module_name` (字符串): 此提交所属的模块名称。此值需要根据您特定的业务逻辑确定，需要您提供更详细的信息，例如如何从提交消息或文件路径中提取模块名称。
    *   `newest_version` (字符串): 此仓库的最新版本标识符 (基于 Tag)。例如 `v1.2.3`。
    *   `next_newest_version` (字符串): 此仓库的次新版本标识符。例如 `v1.2.2`。
    *   `analyze_commit` (布尔值): 是否对此仓库执行提交分析。在 RepoConfig 中指定。
    *   `generate_patch` (布尔值): 是否为此仓库生成补丁文件。在 RepoConfig 中指定。
    *   `branch_info` (字符串): 关于此仓库中分支的文档。
    *   `push_template` (字符串): Git 推送操作的模板。例如 `HEAD:refs/for/{branch}`，其中 `{branch}` 将替换为实际的分支名称。

2. **RepoConfig:** 用于存储代码仓库（例如 `grpower`、`grt`、`yocto` 等）的配置信息以及它所包含的 Git 仓库列表，包含以下字段：
    *   `repo_name` (字符串): 代码仓库的名称。例如 `yocto`、`grpower`。
    *   `repo_type` (字符串): 仓库类型，例如 `git`、`jiri`、`repo`。
    *   `path` (字符串): 仓库根目录的路径。例如 `~/yocto`、`~/grpower`。
    *   `git_repos` (列表): 存储 GitRepoInfo 对象的列表，表示此仓库管理的所有 Git 仓库。
    *   `manifest_path` (字符串, 可选): manifest 文件的路径，仅适用于 `jiri` 和 `repo` 类型。
    *   `default_tag_prefix` (字符串, 可选): 此仓库下所有 Git 仓库的默认标签前缀。
    *   `parent_repo` (字符串): 此仓库的父仓库名称。对于大型项目，可能存在多层嵌套的代码仓库。当前已知的所有仓库此值为 `None`。
    *   `manifest_type` (字符串, 可选): manifest 文件的类型，仅适用于 `jiri` 和 `repo` 类型。值为 `jiri` 或 `repo` 用于指导解析程序使用不同的解析逻辑。
    *   `default_analyze_commit` (布尔值): 是否对此仓库下的所有 Git 仓库执行提交分析。用于生成 GitRepoInfo 的 `analyze_commit`。
    *   `default_generate_patch` (布尔值): 是否为此仓库下的所有 Git 仓库生成补丁文件。用于生成 GitRepoInfo 的 `generate_patch`。
    *   `all_branches` (列表): 此仓库下所有 Git 仓库的分支列表。
    *   `special_branch_repos` (字典): 使用特殊分支的 Git 仓库列表。键是 Git 仓库名称，值是分支名称。

3. **AllReposConfig:** 用于存储所有代码仓库的配置信息，并提供遍历所有 Git 仓库的功能，包含以下字段：
    *   `repo_configs` (字典): 以 RepoConfig 的 `repo_name` 作为键，RepoConfig 对象作为值的字典。

**配置和解析流程：**

1. **配置文件：** 使用 Python 文件定义所有代码仓库的配置信息。
    *   为每个代码仓库创建一个 RepoConfig 实例，并设置其属性
    *   对于 `jiri` 和 `repo` 类型的仓库，需指定 `manifest_type`。根据需要设置 `default_tag_prefix`。
    *   根据需要设置 `default_analyze_commit` 和 `default_generate_patch`。
    *   在 `special_branch_repos` 中配置使用特殊分支的 Git 仓库。
    *   创建一个 AllReposConfig 实例，并将所有 RepoConfig 实例添加到 `repo_configs` 字典中。

2. **解析 Manifest 文件：**
    *   当 RepoConfig 的 `repo_type` 为 `jiri` 或 `repo` 时，根据其 `manifest_path` 指定的 XML 文件，根据 `manifest_type` 使用相应的解析逻辑解析 XML。
    *   基于 XML 文件中的 `<project>` 标签创建 GitRepoInfo 实例，并将其添加到 RepoConfig 的 `git_repos` 列表中。
    *   根据 RepoConfig 中的 `parent_repo`、`default_tag_prefix`,`default_analyze_commit`、`default_generate_patch`、 `all_branches` 给 GitRepoInfo 实例赋值。
    *   如果 Git 仓库名称出现在 `special_branch_repos` 字典中，则使用字典中指定的分支名称，并删除其他分支名称。

3. **遍历所有 Git 仓库：**
    *   AllReposConfig 需要提供一个方法，该方法遍历 `repo_configs` 字典中每个 RepoConfig 的 `git_repos` 列表，返回一个包含所有 GitRepoInfo 对象的迭代器。
    *   后续代码可以遍历此迭代器以获取所有 Git 仓库的信息，无论它们属于哪个代码仓库。可以绕过代码库设置，直接遍历存储所有 Git 仓库数据结构的大数据结构。

**其他 (参考提供的文件目录结构)：**

```
.
├── assisted_workflow.md
├── code_structure.md
├── config
│   ├── config_loader.py
│   ├── default_config.py
│   ├── global_config.py
│   ├── init_config.py
│   ├── __init__.py
│   ├── logging_config.py
│   ├── repos_config.py
│   └── schemas.py
├── core
│   ├── builder.py
│   ├── commit_analyzer.py
│   ├── __init__.py
│   ├── merger.py
│   ├── patch_generator.py
│   ├── repo_manager.py
│   ├── snapshot_manager.py
│   └── tagger.py
├── deep_think.md
├── Design_for_Base.md
├── part1_all.md
├── part1.md
├── release.py
├── user_story_split.md
└── utils
    ├── excel_utils.py
    ├── file_utils.py
    ├── git_utils.py
    ├── __init__.py
    ├── logger.py
    └── tag_utils.py
```

以上提示词应该能够清晰地传达您的需求，方便 LLM 专业人员理解和实现。
