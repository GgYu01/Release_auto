from base_config import BuildInfo

class BuildConfig(BuildInfo):
    def __init__(self):
        super().__init__(
            enable_nebula_sdk=True,
            enable_nebula=False,
            enable_tee=True,
            build_commands={
                'nebula-sdk': [
                    'make nebula-sdk',
                    'make install'
                ],
                'nebula': [
                    'make nebula',
                    'make install'
                ],
                'tee': [
                    'make tee',
                    'make install'
                ]
            },
            commit_message_format={
                'nebula-sdk': "[{cr_number}] nebula-sdk: {title}\n\n[Description]\n{description}\n\n[Test]\nBuild pass and test ok.",
                'nebula': "[{cr_number}] thyp-sdk: {title}\n\n[Description]\n{description}\n\n[Test]\nBuild pass and test ok.",
                'tee': "[{cr_number}] tee: {title}\n\n[Description]\n{description}\n\n[Test]\nBuild pass and test ok."
            },
            tag_version_identifier='v1.2.3'
        )
        self.cr_number = "CR12345"
        self.commit_title = "Add new feature X"
        self.commit_description = """This commit adds feature X which improves performance by 20%.
        
        Additional details can be included here.
        This supports multiple lines for clear explanations."""

BUILD_CONFIG = BuildConfig()
