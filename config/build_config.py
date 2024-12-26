from dataclasses import dataclass, field
from typing import List
from dataclasses import field
import repo_config

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
    commit_type: str = "default"
    commit_description: str = field(default_factory=lambda: BuildConfig.default_commit_description())

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
    def default_commit_description():
        return """
1.fix audio
2.fix reboot
"""

    def generate_commit_message(self) -> str:
        templates = {
            "nebula": f"""[{self.cr_number}] thyp-sdk: {self.commit_title}

[Description]
{self.commit_description}

[Test]
Build pass and test ok.
""",
            "nebula-sdk": f"""[{self.cr_number}] nebula-sdk: {self.commit_title}

[Description]
{self.commit_description}

[Test]
Build pass and test ok.
""",
            "tee": f"""[{self.cr_number}] tee: {self.commit_title}

[Description]
{self.commit_description}

[Test]
Build pass and test ok.
""",
        }

        return templates.get(self.commit_type, f"""[{self.cr_number}] {self.commit_title}

[Description]
{self.commit_description}

[Test]
Build pass and test ok.
""")

BUILD_CONFIG = BuildConfig()
