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
                SyncAction(action_type="mkdir", action_params={"path": "./.jiri_root/bin"}),
                # SyncAction(action_type="rm", action_params={"path": "./.jiri_manifest"}),
                # SyncAction(action_type="rm", action_params={"path": ".config"}),
                # SyncAction(action_type="rm", action_params={"path": ".prebuilts_config"}),
                # SyncAction(action_type="jiri_command", action_params={"command": "import", "args": ["-remote-branch=master", "cci/nebula-main", "ssh://gerrit:29418/manifest"]}),
                # SyncAction(action_type="jiri_command", action_params={"command": "runp", "args": ["git", "checkout", "-f", "JIRI_HEAD", "--detach"]}),
                # SyncAction(action_type="jiri_command", action_params={"command": "update", "args": ["-gc", "-autoupdate=false", "-run-hooks=false", "--attempts=10", "--force-autoupdate=true", "--rebase-all=false", "--rebase-tracked=false", "--rebase-untracked=false", "--show-progress=true", "--color=auto"]}),
                # SyncAction(action_type="jiri_command", action_params={"command": "runp", "args": ["git", "remote", "get-url", "origin", "|", "sed", "'s/gerrit/gerrit-review/'", "|", "xargs", "git", "remote", "set-url", "--push", "origin"]}),
            ],
        ),
        "grpower_sync": SyncStrategyConfig(
            strategy_name="grpower_sync",
            parent_types=["grpower"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
        "grt_grt_be_sync": SyncStrategyConfig(
            strategy_name="grt_grt_be_sync",
            parent_types=["grt", "grt_be"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "clean", "args": ["-fdx"]}),
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
    }
)