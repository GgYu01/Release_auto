from dataclasses import dataclass

@dataclass
class PatchConfig:
    patch_storage_path: str = '/abs/path/to/patch_storage'
    temp_patch_path: str = '/abs/path/to/temp_patch'
    map_patch_to_commits: bool = True
    override_patch_paths: dict = None
    cleanup_strict: bool = True

    @classmethod
    def create(cls):
        return cls(override_patch_paths={'main_manifest_repo':{'commit_id_abc123':'/new/path/to/override.patch'}})

PATCH_CONFIG = PatchConfig.create()