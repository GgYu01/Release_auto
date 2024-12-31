
Please give me the corresponding code according to my requirement, you can modify the file name, path, create file, delete file appropriately.

**Overall code base requirements:**

1. **Highly modular:** The code must be highly modularized to facilitate subsequent expansion and maintenance.
2. **Focus only on configurability and flexibility:** Do not consider security, performance, and resource consumption, and focus only on code configurability and flexibility.
3. **Prefer to use Python libraries:** Use Python libraries or third-party packages to implement functionality as much as possible, and avoid using Bash commands.
4. **Complete Exception Handling:** Use a complete exception handling mechanism to ensure stable code operation.
5. **Independent and Flexible Configuration System:** The configuration system must be comprehensive, independently manageable, and flexible enough to control functionality without modifying code.
6. **No comments:** No comments or docstring of any kind are allowed in the code. 7.
7. **Take advantage of Python's advanced features:** A modular structure needs to take full advantage of Python's advanced features, such as decorators, classes, plugin architecture, extension modules, context managers, dependency injection, etc.
8. **Follow Best Practices:** Following best practices ensures that the code is clear, concise, robust, and has a flexible package structure.
9. **Rich Logging Output:** The code should support tracing and rich message output, and the logging part should be detailed using rich logging library.

** Code base information definition and management:**

* **Configuration method:** Use Python files and data structures to define all code repository information, and prohibit the use of other configuration file formats such as JSON, YAML, and so on. It is required to use Python code files directly to define the configuration, and not to use any other format of configuration files.
* **Repository information:** You need to be able to define information about each code repository, including:
    * Repository name (repo\_name)
    * Repository type (repo\_type): including `git`, `jiri` and `repo` types.
    * Repository path
    * The tag prefix (tag\_prefix).
    * Remote repository name (remote\_name)
    * Remote branch name (remote\_branch)
* **Specific repository definitions:**
    * `grpower`: git repository at `~/grpower`.
    * `grt`: git repository at `~/grt`.
    * `grt_be`: git repository at `~/grt_be`.
    * `nebula`: jiri repository at `~/grpower/workspace/nebula`.
    * `yocto`: repo repository, path is `~/yocto`.
    * `alps`: repository at `~/alps`.
* ** Special handling of jiri and repo repositories:** ** Need to parse jiri and repo repositories.
    * Need to parse the manifest files of the jiri and repo repositories.
    * Treat jiri and repo repositories as a collection of separate git repositories.
    * Completely deprecate the native jiri and repo tools.
* **manifest file example: **
    * **repo manifest example: **

        <?xml version=“1.0” encoding=“UTF-8”?
        <?xml version=“1.0” encoding=“UTF-8”? <?xml version=“1.0” encoding=“UTF-8”?
        <manifest
          <remote fetch=”...” name=“grt-mt8678” review=“https://www.goldenriver.com.cn:3443”/>
          <project name=“yocto/src/connectivity/gps/4.0” path=“src/connectivity/gps/4.0”/>
          <project name=“yocto/src/tinysys/common” path=“src/tinysys/common”/>
        </manifest
        ```
    * ** Example of a jiri manifest: **

        `` **xml
        <manifest version=“1.1”>
          <projects>
            <project name=“build” path=“build” remote=“ssh://gerrit:29418/build” remotebranch=“nebula” gerrithost=“http://gerrit” githooks="manifest /git-hooks"/>
            <project name=“docs” path=“docs” remote=“ssh://gerrit:29418/docs” remotebranch=“nebula” gerrithost=“http://gerrit” githooks="manifest/ git-hooks” />
        </manifest
        ```

**Data structure design:**

The following three core data structures need to be created to store and manage repository information:

1. **GitRepoInfo:** Used to store the details of a single Git repository, including the following fields:
    * `repo_name` (string): The name of the Git repository. For example, `yocto/src/connectivity/gps/4.0` or `grpower`. * `repo_parent` (string): The name of the Git repository.
    * `repo_parent` (string): The parent of the Git repository, as defined in the RepoConfig section.
    * `path` (string): The local path to the Git repository. For example, `~/grpower` or `~/grpower/workspace/nebula/build`. * `repo_type`: The parent repository of the Git repository, as defined in the RepoConfig section.
    * `repo_type` (string): The type of the repository, e.g. `git`, `jiri`, `repo`.
    * `tag_prefix` (string): The tag prefix used by this Git repository.
    * `remote_name` (string): The name of the remote repository. For example, `grt-mt8678`.
    * `remote_branch` (string): The name of the remote branch. For example, `nebula`.
    * `parent_repo` (string): The name of the RepoConfig that points to this Git repository (e.g. `yocto`, `nebula`). Use this to, for example, know the path to a Git repository by backtracking to `repo_type`.
    * :: `commit_analyses` (list): Used to store commit analyses for Git repositories. Each analysis is a dictionary containing the following keys:
        * `commit_id` (string): The SHA-1 hash of the commit.
        * `message` (string): The commit message.
        * `patch_file` (string): Path to the patch file generated by `format-patch`.
        * `module_name` (string): The name of the module this commit belongs to. This value needs to be determined based on your specific business logic and requires you to provide more detailed information, such as how to extract the module name from the commit message or file path.
    * `newest_version` (string): The latest version identifier for this repository (based on Tag). For example, `v1.2.3`.
    * `next_newest_version` (string): Identifier of the next newest version of the repository. For example, `v1.2.2`.
    * `analyze_commit` (boolean): Whether to perform a commit analysis on this repository. Specified in RepoConfig.
    * `generate_patch` (boolean): Whether to generate a patch file for this repository. Specified in RepoConfig.
    * `branch_info` (string): Documentation about the branches in this repository.
    * `push_template` (string): Template for Git push operations. For example, `HEAD:refs/for/{branch}`, where `{branch}` will be replaced with the actual branch name. 2. **RepoConfiguration: The repository's repository template.

2. **RepoConfig:** Used to store configuration information for a code repository (e.g., `grpower`, `grt`, `yocto`, etc.) and a list of Git repositories it contains, containing the following fields:
    * `repo_name` (string): The name of the code repository. For example, `yocto`, `grpower`.
    * `repo_type` (string): The type of the repository, e.g. `git`, `jiri`, `repo`.
    * `path` (string): Path to the root directory of the repository. For example `~/yocto`, `~/grpower`.
    * `git_repos` (list): A list of GitRepoInfo objects that represent all Git repositories managed by this repository.
    * `manifest_path` (string, optional): Path to the manifest file, only available for `jiri` and `repo` types.
    * `default_tag_prefix` (string, optional): Default tag prefix for all Git repositories under this repository.
    * `parent_repo` (string): The name of the parent repository for this repository. For large projects, there may be multiple nested code repositories. This value is `None` for all currently known repositories.
    * `manifest_type` (string, optional): The type of manifest file, applicable only to `jiri` and `repo` types. A value of `jiri` or `repo` is used to direct the parsing program to use different parsing logic.
    * `default_analyze_commit` (boolean): Whether to perform commit analysis on all Git repositories under this repository. `analyze_commit` is used to generate GitRepoInfo.
    * `default_generate_patch` (boolean): Whether to generate patch files for all Git repositories under this repository. `generate_patch` for GitRepoInfo generation.
    * `all_branches`: A list of branches for all Git repositories under this repository.
    * `special_branch_repos` (dictionary): List of Git repositories that use special branches. The key is the name of the Git repository and the value is the branch name. 3. **AllRepositories_Repo

3. **AllReposConfig:** Used to store configuration information for all code repositories and provide the ability to traverse all Git repositories, contains the following fields:
    * `repo_configs` (dictionary): a dictionary with RepoConfig's `repo_name` as the key and the RepoConfig object as the value.

**Configuration and parsing process:**

1. **Configuration files:** Use Python files to define configuration information for all code repositories.
    * Create a RepoConfig instance for each code repository and set its properties
    * For `jiri` and `repo` type repositories, specify `manifest_type`. Set `default_tag_prefix` as needed.
    * Set `default_analyze_commit` and `default_generate_patch` as needed.
    * Configure Git repositories that use special branches in `special_branch_repos`.
    * Create an AllReposConfig instance and add all RepoConfig instances to the `repo_configs` dictionary.

2. ** Parse the Manifest file:**
    * When the `repo_type` of a RepoConfig is `jiri` or `repo`, parses the XML file specified by its `manifest_path` using the appropriate parsing logic based on the `manifest_type`.
    * Create a GitRepoInfo instance based on the `<project>` tag in the XML file and add it to the `git_repos` list in RepoConfig.
    * Assign a value to the GitRepoInfo instance based on the `parent_repo`, `default_tag_prefix`,`default_analyze_commit`, `default_generate_patch`, `all_branches` in RepoConfig. GitRepoInfo.
    * If the Git repository name appears in the `special_branch_repos` dictionary, the branch name specified in the dictionary is used and the other branch names are removed.

3. ** Iterate over all Git repositories:**
    * AllReposConfig needs to provide a method that iterates over the `git_repos` list for each RepoConfig in the `repo_configs` dictionary, returning an iterator containing all GitRepoInfo objects.
    * Subsequent code can iterate over this iterator to get information about all Git repositories, regardless of which code repository they belong to. It is possible to bypass the code repository setup and directly traverse the big data structure that stores the data structures of all Git repositories.

**Other (refer to the supplied file directory structure):**

```
.
├── assisted_workflow.md
├── code_structure.md
├── config
│ ├── config_loader.py
│ ├── default_config.py
│ ├── global_config.py
│ ├── init_config.py
│ ├── __init__.py
│ ├── logging_config.py
│ ├── repos_config.py
│ └── schemas.py
├── core
│ ├── builder.py
│ ├── commit_analyzer.py
│ ├── __init__.py
│ ├── merger.py
│ ├── patch_generator.py
│ ├── repo_manager.py
│ ├── snapshot_manager.py
│ └── tagger.py
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
    ├─ logger.py
    └── tag_utils.py
