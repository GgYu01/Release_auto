from dataclasses import dataclass

@dataclass
class RemoteConfig:
    remote_host: str = 'remote.server.com'
    remote_user: str = 'deployer'
    remote_path: str = '/remote/deploy/path'
    archive_file_naming_rule: str = 'MTK_{latest_tag}'
    create_parent_structure: bool = True
    transfer_command: str = 'scp'

REMOTE_CONFIG = RemoteConfig()