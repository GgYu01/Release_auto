from dataclasses import dataclass
from typing import Dict

@dataclass
class BuildConfig:
    enable_nebula_sdk: bool = True
    enable_nebula: bool = False
    enable_tee: bool = True
    build_commands: dict = None
    commit_message_format: dict = None
    tag_version_identifier: str = 'v1'
    cr_number: str = "CR1"
    commit_title: str = "new feature"
    commit_description: str = "This"

    @staticmethod
    def parse_multiline_commands(commands: str) -> dict:
        parsed_commands = {}
        for block in commands.strip().split("\n\n"):
            lines = block.strip().split("\n")
            key = lines[0].strip(" :")
            parsed_commands[key] = lines[1:]
        return parsed_commands

    @staticmethod
    def parse_multiline_description(description: str) -> str:
        return description.strip()

    @staticmethod
    def default_build_commands():
        commands = """
        nebula-sdk : 
        rm -rf out
        cd ~/nebula/
        source scripts/env.sh
        make nebula-sdk
        make install

        nebula : 
        rm -rf out
        cd ~/grpower/ 
        source scripts/env.sh
        gr-nebula.py build

        tee : 
        make tee
        make install
        """
        return BuildConfig.parse_multiline_commands(commands)

    @staticmethod
    def default_commit_message_format():
        description = """
        1.fix audio
        2.fix reboot
        3.fix suspend
        """
        return BuildConfig.parse_multiline_description(description)

    @classmethod
    def create(cls):
        return cls(
            build_commands=cls.default_build_commands(),
            commit_message_format={
                "description": cls.default_commit_message_format()
            },
        )

BUILD_CONFIG = BuildConfig.create()
