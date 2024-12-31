好的，让我们开始拆解你的用户故事。根据你的描述，我们可以将这个复杂的任务分解成多个更小的、独立的用户故事，每个故事都专注于一个特定的功能模块。我会尽可能详细地描述每个用户故事，并规划相应的数据结构和配置文件。

**主用户故事:**

作为一名开发者，我希望能够对使用不同 manifest 管理的大量子 Git 仓库和独立的 Git 仓库一起执行 release 任务，包括打标签、生成补丁、编译、更新远端仓库等操作，以便进行版本发布。

**子用户故事拆解:**

**1. 配置管理模块**

*   **用户故事 1.1:** 作为一名开发者，我希望能够通过一个 Python 配置文件来定义所有代码仓库的信息，包括仓库名、类型（独立仓库或 manifest 管理的仓库）、路径、标签前缀等，以便程序能够识别和管理这些仓库。
*   **用户故事 1.2:** 作为一名开发者，我希望能够通过一个 Python 配置文件来定义所有仓库的初始化信息，包括初始化 commit、最新/次新 tag 版本标识、是否生成 patch 等，以便在 release 过程中使用这些信息进行各种操作。
*   **用户故事 1.3:** 作为一名开发者，我希望能够通过一个 Python 配置文件来定义日志输出的路径和等级，以便查看程序运行过程中的详细信息。
*   **用户故事 1.4:** 作为一名开发者，我希望能够通过一个 Python 配置文件来定义全局参数，例如要打的 TAG 版本标识、分支、描述信息、CR、title、commit message 格式、是否需要执行 nebula-sdk、nebula、TEE 的更新等，以便在 release 过程中使用这些参数。
*   **用户故事 1.5:** 作为一名开发者，我希望配置文件能够支持从外部 JSON 或 YAML 文件导入并覆盖部分配置项的默认值，以便灵活地调整配置参数。

**2. 仓库信息初始化模块**

*   **用户故事 2.1:** 作为一名开发者，我希望程序能够根据配置文件中的仓库信息，初始化一个包含所有仓库详细信息的数据结构，以便后续模块可以方便地访问和使用这些信息。

**3. 仓库更新模块**

*   **用户故事 3.1:** 作为一名开发者，我希望程序能够根据配置文件中的指定分支，对每个仓库执行特定的命令来更新代码，以便所有仓库都处于最新的状态。
*   **用户故事 3.2:** 作为一名开发者，我希望程序能够支持针对特定仓库配置特殊的分支名，以便在更新这些仓库时使用指定的分支。

**4. 编译模块**

*   **用户故事 4.1:** 作为一名开发者，我希望程序能够根据配置文件中的指示，判断是否需要执行 nebula-sdk、nebula 或 TEE 的编译操作，以便在需要时生成最新的二进制文件。
*   **用户故事 4.2:** 作为一名开发者，我希望程序能够在编译前对特定的仓库更新 git tag，以便编译基于正确的代码版本。
*   **用户故事 4.3:** 作为一名开发者，我希望程序能够根据不同的编译配置，执行不同的编译命令，并在不同的仓库进行提交，并使用不同的 commit 信息格式内容，以便区分不同的编译任务。
*   **用户故事 4.4:** 作为一名开发者，我希望程序能够将编译生成的二进制文件推送到远端仓库，以便进行后续的发布操作。

**5. 合并请求处理模块**

*   **用户故事 5.1:** 作为一名开发者，我希望程序能够提供选项，让用户选择手动合并远端仓库的合并请求，或者自动执行合并操作，以便控制 release 流程的进度。

**6. 打标签模块**

*   **用户故事 6.1:** 作为一名开发者，我希望程序能够根据配置文件中的标签前缀和全局 TAG 版本标识，为所有仓库打上新的 TAG，以便标记 release 版本。

**7. 获取 Excel 文件模块**

*   **用户故事 7.1:** 作为一名开发者，我希望程序能够获取指定的 Excel 文件，以便后续将 commit 信息写入该文件。

**8. 获取最新/次新 TAG 模块**

*   **用户故事 8.1:** 作为一名开发者，我希望程序能够获取指定仓库的最新和次新 TAG，并提取其中的版本标识，以便进行后续的 commit 差异分析。
*   **用户故事 8.2:** 作为一名开发者，我希望程序能够避免在同一个 commit 上被先后创建多个 TAG 导致获取 TAG 不正确的问题，以确保获取到正确的最新和次新 TAG。

**9. Commit 差异分析模块**

*   **用户故事 9.1:** 作为一名开发者，我希望程序能够根据仓库的最新和次新 TAG，获取两个 TAG 之间的所有 commit，并记录 commit ID 和 commit 正文，以便生成变更日志。
*   **用户故事 9.2:** 作为一名开发者，我希望程序能够识别 commit 正文中的特殊信息，并使用 `git format-patch` 命令生成对应的 patch 文件，并记录 patch 文件的绝对路径，以便后续处理这些特殊的 commit。
*   **用户故事 9.3:** 作为一名开发者，我希望程序能够支持配置某些路径的仓库不执行 commit 差异分析，以便跳过不需要分析的仓库。

**10. Patch 生成与管理模块**

*   **用户故事 10.1:** 作为一名开发者，我希望程序能够根据仓库的配置，判断每个仓库是否需要生成 patch，并在需要时使用 `git format-patch` 命令生成两个 TAG 之间的所有 patch 文件，以便提供补丁更新。
*   **用户故事 10.2:** 作为一名开发者，我希望程序能够在数据结构中记录每个子 Git 仓库对应的多个 commit 和每个 commit 对应的 patch 文件，以便建立 commit 和 patch 文件之间的对应关系。
*   **用户故事 10.3:** 作为一名开发者，我希望程序能够支持将特殊 commit 对应的 patch 文件的绝对路径强制覆盖到某些父仓库对应所有子 Git 或独立 Git 仓库每个 commit 所对应的 patch 记录中，以便将特定的补丁应用到相关的仓库。
*   **用户故事 10.4:** 作为一名开发者，我希望程序能够在生成 patch 文件时记录每个 patch 文件的绝对路径，并在操作全部结束后删除这些临时生成的 patch 文件，以便清理临时文件。

**11. Excel 写入模块**

*   **用户故事 11.1:** 作为一名开发者，我希望程序能够根据一定的规则将 commit 信息对应的 ID 等写入 Excel 表格中，以便生成变更报告。

**12. 远端目录构建与文件传输模块**

*   **用户故事 12.1:** 作为一名开发者，我希望程序能够根据 repo parent 生成文件夹和压缩包，并在远端构造 MTK_{最新tag} 的文件夹，然后根据相对路径放入 patch 文件，以便构建发布目录结构。
*   **用户故事 12.2:** 作为一名开发者，我希望程序能够将生成的压缩包传输到远端服务器，以便完成发布流程。

**13. 快照保存模块**

*   **用户故事 13.1:** 作为一名开发者，我希望程序能够在每次 release 后保存当前代码的快照，以便后续回溯或对比不同版本的代码。
**数据结构规划 (Python):**

```python
# config_repo.py  仓库配置相关
class RepositoryConfig:
    def __init__(self):
        self.repositories = []  # 仓库列表

    def add_repository(self, repo_name, repo_type, path=None, tag_prefix=None, manifest_file=None, parent_repo=None, module=None):
        repo_info = {
            "name": repo_name,
            "type": repo_type,  # "independent" or "manifest"
            "path": path,  # 独立仓库的绝对路径
            "tag_prefix": tag_prefix,
            "manifest_file": manifest_file,  # manifest 仓库的 manifest 文件路径
            "parent_repo": parent_repo,  # manifest仓库的父仓库，配置管理用
            "module": module, #所属模块
            "initial_commit" : None,
            "latest_tag": None,  # 最新 tag 版本标识
            "previous_tag": None,  # 次新 tag 版本标识
            "generate_patch": False,  # 是否生成 patch
            "branches" : {}, #每个仓库可以自定义的分支名，key为仓库名，value为分支名。
            "skip_commit_analysis": False,  # 是否跳过 commit 分析
            "commits": [],  # { "id": "", "message": "", "patch_file": "" }
            "special_commits" : [], #特殊commit的id列表
        }
        self.repositories.append(repo_info)

    def update_from_external(self, data):
        #从外部导入配置，支持json以及yaml。
        if isinstance(data, dict):
            for key in data:
                if hasattr(self,key):
                    setattr(self,key,data[key]) #更新当前实例的属性
                else:
                    #针对仓库的属性值更新
                    for repo in self.repositories:
                        if key == repo['name']:
                            repo.update(data[key])

#config_global.py 全局参数配置相关
class GlobalConfig:
    def __init__(self):
        self.tag_version = None  # TAG 版本标识
        self.default_branch = "master"  # 默认分支
        self.description = ""  # 描述信息
        self.cr = ""  # CR
        self.title = ""  # title
        self.commit_message_format = ""  # commit message 格式
        self.update_nebula_sdk = False  # 是否更新 nebula-sdk
        self.update_nebula = False  # 是否更新 nebula
        self.update_tee = False  # 是否更新 TEE
        self.log_file = "release.log"  # 日志文件路径
        self.log_level = "INFO"  # 日志输出等级
        self.excel_file = "release_report.xlsx"  # Excel 文件路径
        self.remote_server = "example.com"  # 远端服务器地址
        self.remote_base_path = "/path/to/release"  # 远端基础路径
        self.patch_temp_dir = "/tmp/release_patches" #patch临时存储路径

    def update_from_external(self, data):
        # 从外部导入配置，支持json以及yaml。
        if isinstance(data, dict):
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)

# config_build.py 编译配置相关
class BuildConfig:
    def __init__(self):
        self.build_commands = {
            "nebula-sdk": {
                "command": "build_nebula_sdk.sh",
                "repo": "nebula-sdk",
                "commit_message": "Update nebula-sdk",
                "target_branch": "master"
            },
            "nebula": {
                "command": "build_nebula.sh",
                "repo": "nebula",
                "commit_message": "Update nebula",
                "target_branch": "master"
            },
            "tee": {
                "command": "build_tee.sh",
                "repo": "tee",
                "commit_message": "Update TEE",
                "target_branch": "develop"
            },
        }

    def update_from_external(self,data):
        if isinstance(data, dict):
            for key in data:
                if key in self.build_commands:
                    self.build_commands[key].update(data[key])
```

**配置文件示例 (config.py):**

```python
from config_repo import RepositoryConfig
from config_global import GlobalConfig
from config_build import BuildConfig
import json
import yaml
import os

# 仓库配置
repository_config = RepositoryConfig()
repository_config.add_repository("repo1", "independent", path="/path/to/repo1", tag_prefix="REPO1_", module='moduleA')
repository_config.add_repository("repo2", "manifest", manifest_file="manifest.xml", tag_prefix="REPO2_", parent_repo='parent_repo', module="moduleB")
repository_config.add_repository("repo3", "independent", path="/path/to/repo3", tag_prefix="REPO3_", module='moduleC')
repository_config.repositories[0]['branches']['repo1'] = "branch_for_repo1"  # 为 repo1 设置特殊分支
repository_config.repositories[2]['skip_commit_analysis'] = True #repo3无需分析commit
# 从外部 JSON 文件更新仓库配置
if os.path.exists("repo_config_override.json"):
    with open("repo_config_override.json", "r") as f:
        repo_data = json.load(f)
        repository_config.update_from_external(repo_data)

# 从外部 YAML 文件更新仓库配置
if os.path.exists("repo_config_override.yaml"):
    with open("repo_config_override.yaml", "r") as f:
        repo_data = yaml.safe_load(f)
        repository_config.update_from_external(repo_data)

# 全局配置
global_config = GlobalConfig()
global_config.tag_version = "1.0.0"
global_config.description = "Release 1.0.0"
global_config.update_nebula_sdk = True

# 从外部 JSON 文件更新全局配置
if os.path.exists("global_config_override.json"):
    with open("global_config_override.json", "r") as f:
        global_data = json.load(f)
        global_config.update_from_external(global_data)

# 编译配置
build_config = BuildConfig()
#您可以根据实际情况自定义具体编译命令等
# 从外部 YAML 文件更新编译配置
if os.path.exists("build_config_override.yaml"):
    with open("build_config_override.yaml", "r") as f:
        build_data = yaml.safe_load(f)
        build_config.update_from_external(build_data)
```

**总结:**

通过以上拆解，我们将原本复杂的用户故事分解成了多个更小的、可独立开发和测试的子用户故事。每个子用户故事都对应一个特定的功能模块，并且定义了清晰的接口和依赖关系。通过配置模块定义的数据结构，各个模块可以方便地共享和访问所需的信息，实现了高度的模块化和低耦合。同时，使用 Python 配置文件可以灵活地配置各种参数，并通过外部 JSON 或 YAML 文件进行覆盖，提高了配置的灵活性和可扩展性。

请记住，这只是一个初步的拆解和规划，在实际开发过程中，你可能需要根据具体情况进行调整和细化。但这个框架为你提供了一个良好的起点，帮助你构建一个模块化、可配置、易于维护的 release 系统。
