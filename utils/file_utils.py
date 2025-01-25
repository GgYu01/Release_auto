import os
from utils.custom_logger import Logger

logger = Logger("file_utils")

def construct_path(base_path, relative_path):
    try:
        expanded_base_path = os.path.expanduser(base_path)
        return os.path.join(expanded_base_path, relative_path)
        # return os.path.abspath(os.path.join(base_path, relative_path))
    except Exception as e:
        logger.error(f"Error constructing path: {e}")
        return None
