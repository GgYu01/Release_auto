import os
from utils.rich_logger import RichLogger

logger = RichLogger("file_utils")

def construct_path(base_path, relative_path):
    try:
        return os.path.abspath(os.path.join(base_path, relative_path))
    except Exception as e:
        logger.error(f"Error constructing path: {e}")
        return None
