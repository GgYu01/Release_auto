import os
import shutil
import glob
from typing import List, Optional
from utils.custom_logger import Logger

logger: Logger = Logger("file_utils")

def construct_path(base_path: str, relative_path: str) -> Optional[str]:
    try:
        expanded_base_path = os.path.expanduser(base_path)
        return os.path.join(expanded_base_path, relative_path)
        # return os.path.abspath(os.path.join(base_path, relative_path))
    except Exception as e:
        logger.error(f"Error constructing path: {e}")
        return None

class FileOperator:
    def __init__(self) -> None:
        self.logger = Logger(self.__class__.__name__)

    def remove_directory_recursive(self, path: str) -> bool:
        try:
            if not os.path.exists(path):
                self.logger.info(f"Directory does not exist: {path}")
                return True
            
            self.logger.info(f"Removing directory recursively: {path}")
            shutil.rmtree(path, ignore_errors=True)
            
            if os.path.exists(path):
                self.logger.error(f"Failed to remove directory: {path}")
                return False
                
            self.logger.info(f"Successfully removed directory: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing directory {path}: {e}")
            return False

    def copy_file(self, src_path: str, dst_path: str) -> bool:
        try:
            if not os.path.exists(src_path):
                self.logger.error(f"Source file does not exist: {src_path}")
                return False

            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)

            self.logger.info(f"Copying file from {src_path} to {dst_path}")
            shutil.copy2(src_path, dst_path)
            
            if not os.path.exists(dst_path):
                self.logger.error(f"Failed to copy file to: {dst_path}")
                return False
                
            self.logger.info(f"Successfully copied file to: {dst_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error copying file from {src_path} to {dst_path}: {e}")
            return False

    def create_directory(self, path: str) -> bool:
        try:
            if os.path.exists(path):
                self.logger.info(f"Directory already exists: {path}")
                return True

            self.logger.info(f"Creating directory: {path}")
            os.makedirs(path, exist_ok=True)
            
            if not os.path.exists(path):
                self.logger.error(f"Failed to create directory: {path}")
                return False
                
            self.logger.info(f"Successfully created directory: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {e}")
            return False

    def copy_wildcard(self, src_pattern: str, dst_dir: str) -> bool:
        try:
            if not os.path.exists(dst_dir):
                self.create_directory(dst_dir)

            matched_files = glob.glob(src_pattern)
            if not matched_files:
                self.logger.warning(f"No files match pattern: {src_pattern}")
                return True

            self.logger.info(f"Copying files matching {src_pattern} to {dst_dir}")
            success = True
            
            for src_file in matched_files:
                dst_path = os.path.join(dst_dir, os.path.basename(src_file))
                if not self.copy_file(src_file, dst_path):
                    success = False

            if success:
                self.logger.info(f"Successfully copied all matching files to: {dst_dir}")
            else:
                self.logger.warning(f"Some files failed to copy to: {dst_dir}")
                
            return success
        except Exception as e:
            self.logger.error(f"Error copying files from {src_pattern} to {dst_dir}: {e}")
            return False
