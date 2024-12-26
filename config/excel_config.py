from dataclasses import dataclass

@dataclass
class ExcelConfig:
    excel_output_path: str = '/abs/path/to/output_info.xlsx'
    include_commit_id: bool = True
    include_commit_msg: bool = True
    other_metadata: dict = None

    @classmethod
    def create(cls):
        return cls(other_metadata={'sheet_name':'Release_Notes','columns':['Repo','CommitID','Message','Tag','Date']})

EXCEL_CONFIG = ExcelConfig.create()
