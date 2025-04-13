import re
import datetime
import logging
from typing import Dict, Union, Optional, List, Any
from utils.custom_logger import Logger

logger = Logger(__name__)

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


def extract_version_identifier(tag: str, prefix: Optional[str]) -> Optional[str]:
    if not tag:
        logger.warning("Cannot extract identifier from None or empty tag.")
        return None

    if prefix:
        if tag.startswith(prefix):
            identifier = tag[len(prefix):]
            if not identifier:
                logger.warning(f"Extracted empty identifier for tag '{tag}' with prefix '{prefix}'.")
                return None
            logger.debug(f"Extracted identifier '{identifier}' from tag '{tag}' using prefix '{prefix}'.")
            return identifier
        else:
            logger.warning(f"Tag '{tag}' does not start with the expected prefix '{prefix}'. Cannot extract identifier.")
            return None
    else:
        logger.warning("No prefix provided. Cannot reliably extract version identifier from tag.")
        return None


def construct_tag(prefix: Optional[str], version_identifier: str) -> str:
    if not version_identifier:
        raise ValueError("Version identifier cannot be empty when constructing a tag.")

    if prefix:
        constructed_tag = f"{prefix}{version_identifier}"
    else:
        constructed_tag = version_identifier

    logger.debug(f"Constructed tag '{constructed_tag}' using prefix '{prefix}' and identifier '{version_identifier}'.")
    return constructed_tag
