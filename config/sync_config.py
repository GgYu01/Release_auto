from config.schemas import AllSyncConfigs, SyncStrategyConfig, SyncAction

sync_strategies_config = AllSyncConfigs(
    sync_configs={
        "alps_yocto_sync": SyncStrategyConfig(
            strategy_name="alps_yocto_sync",
            parent_types=["alps", "yocto"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "fetch", "args": ["--all"]}),
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_name}/{remote_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "clean", "args": ["-fdx"]}),
            ],
        ),
        "nebula_sync": SyncStrategyConfig(
            strategy_name="nebula_sync",
            parent_types=["nebula"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_name}/{remote_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
        "grpower_sync": SyncStrategyConfig(
            strategy_name="grpower_sync",
            parent_types=["grpower"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_name}/{remote_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
        "grt_grt_be_sync": SyncStrategyConfig(
            strategy_name="grt_grt_be_sync",
            parent_types=["grt", "grt_be"],
            sync_actions=[
                SyncAction(action_type="git_command", action_params={"command": "checkout", "args": ["-f", "{local_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "reset", "args": ["--hard", "{remote_name}/{remote_branch}"]}),
                SyncAction(action_type="git_command", action_params={"command": "clean", "args": ["-fdx"]}),
                SyncAction(action_type="git_command", action_params={"command": "pull", "args": []}),
            ],
        ),
    }
)