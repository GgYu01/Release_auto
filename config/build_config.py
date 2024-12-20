from dataclasses import dataclass
from typing import List
from dataclasses import field

@dataclass
class BuildModule:
    name: str
    commands: str

@dataclass
class BuildConfig:
    enable_nebula_sdk: bool = False
    enable_nebula: bool = True
    enable_tee: bool = False
    build_commands: List[BuildModule] = field(default_factory=lambda: BuildConfig.default_build_commands())
    tag_version_identifier: str = '20241218_01'
    cr_number: str = "alps0001"
    commit_title: str = "new feature"
    commit_description: str = BuildConfig.default_commit_description()

    @staticmethod
    def default_build_commands():
        return [
            BuildModule(
                name="nebula-sdk",
                commands="""
make nebula-sdk
"""
            ),
            BuildModule(
                name="nebula",
                commands="""
source scripts/env.sh
gr-nebula.py build
"""
            ),
            BuildModule(
                name="tee",
                commands="""
make tee
"""
            ),
        ]

    @staticmethod
    def default_commit_message_format():
        return """
1.fix audio
2.fix reboot
"""

BUILD_CONFIG = BuildConfig()
