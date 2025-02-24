我需要完成一个高度模块化项目的一部分的任务细化和技术设计，提供给我完整、详细的设计，设计部分仅允许你发送文字。在我审查后，我会用你的本次回答指导下一个LLM生成代码。禁止你提供任何代码。你需要输出的是给下一个用于生成代码的LLM的prompt。你的回答中请不要包含任何的代码和伪代码，应该是纯语言文字。


*   **用户故事 1.2:** 作为一名开发者，我希望能够读取现有的数据结构，这个数据结构已经记录了所有git仓库的参数，来定义所有仓库的初始化信息，包括初始化 commit、最新/次新 tag 版本标识、是否生成 patch 等，以便在 release 过程中使用这些信息进行各种操作。
我现有的代码已经完成了根据repo jiri代码库把manifest下对应所有子git仓库都做解析为了独立的git仓库。现在我有一个大数据结构记录了所有git、repo、jiri对应的git仓库，现在我需要你根据repo parent等信息来对不同git仓库进行赋值。

我目前的项目路径是~/Release_auto，
nebula@ab2c1af07fa4:~/Release_auto $ tree
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
├── part1_LLM_generate_code.md
├── part1.md
├── part2.md
├── release.py
├── user_story_split.md
└── utils
    ├── excel_utils.py
    ├── file_utils.py
    ├── git_utils.py
    ├── __init__.py
    ├── rich_logger.py
    └── tag_utils.py

其中，子路径config/repos_config.py记录了代码库下，我希望给所有子git仓库赋值的内容。
比如部分源码如下：
@dataclass
class GitRepoInfo:
    repo_name: str
    repo_parent: str
    path: str
    repo_type: str
    tag_prefix: Optional[str] = None
    remote_name: Optional[str] = None
    remote_branch: Optional[str] = None
    parent_repo: Optional[str] = None
    commit_analyses: List[Dict] = field(default_factory=list)
    newest_version: Optional[str] = None
    next_newest_version: Optional[str] = None
    analyze_commit: bool = False
    generate_patch: bool = False
    branch_info: Optional[str] = None
    push_template: Optional[str] = None

nebula_config = RepoConfig(
    repo_name="nebula",
    repo_type="jiri",
    path="~/grpower/workspace/nebula",
    manifest_path="/home/nebula/grpower/workspace/nebula/manifest/cci/nebula-main",
    manifest_type="jiri",
    default_tag_prefix="release-spm.mt8678_mt8676_",
    default_analyze_commit=True,
    default_generate_patch=False,
    all_branches=["nebula"],
    special_branch_repos={"zircon":"release-spm.mt8678_mtk","garnet":"release-spm.mt8678_mtk"}
)
我希望repo parent是nebula的仓库，使用nebula_config赋值部分变量，repo name应该保持原有每个git仓库自己数据结构的内容，path也不应该改变，default_tag_prefix应该给对应git仓库的数据结构中tag_prefix赋值，default_analyze_commit给commit_analyses赋值，default_generate_patch给generate_patch赋值，branch_info需要特殊处理，正常应该使用all_branches的内容，但是如果git对应的repo name符合special_branch_repos中的内容，则branch应该用special_branch_repos记录的分支。