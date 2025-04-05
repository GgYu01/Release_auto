import re
import datetime
from typing import Dict, Union, Optional


class InvalidVersionIdentifierFormatError(ValueError):
    pass


def parse_version_identifier(version_identifier: str) -> Dict[str, Union[datetime.date, int]]:
    pattern = r"^(\d{4})_(\d{2})(\d{2})_(\d{2})$"
    match = re.match(pattern, version_identifier)
    
    if not match:
        raise InvalidVersionIdentifierFormatError(
            f"Invalid version identifier format: {version_identifier}")
    
    try:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        counter = int(match.group(4))
        
        tag_date = datetime.date(year, month, day)
        return {"date": tag_date, "counter": counter}
    except ValueError:
        raise InvalidVersionIdentifierFormatError(
            f"Invalid date components in version identifier: {version_identifier}")


def generate_next_version_identifier(
    current_time: datetime.datetime,
    last_sequence: int
) -> str:
    return current_time.strftime(f"%Y_%m%d_{(last_sequence + 1):02d}")
