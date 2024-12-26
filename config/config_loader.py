import json
import yaml
import os

from .repo_config import REPO_CONFIG
from .build_config import BUILD_CONFIG
from .logging_config import LOGGING_CONFIG
from .patch_config import PATCH_CONFIG
from .excel_config import EXCEL_CONFIG
from .remote_config import REMOTE_CONFIG

def load_external_configs(json_path=None, yaml_path=None):
    external_data = {}
    if json_path and os.path.exists(json_path):
        with open(json_path, 'r') as jf:
            external_data.update(json.load(jf))
    if yaml_path and os.path.exists(yaml_path):
        with open(yaml_path, 'r') as yf:
            external_data.update(yaml.safe_load(yf))
    return external_data

def merge_config(base, overrides):
    if isinstance(base, dict) and isinstance(overrides, dict):
        for k, v in overrides.items():
            if k in base and isinstance(base[k], dict):
                base[k] = merge_config(base[k], v)
            else:
                base[k] = v
    return base

def finalize_config(json_path=None, yaml_path=None):
    final_config = {
        'repositories': REPO_CONFIG,
        'build': {k:v for k,v in vars(BUILD_CONFIG).items() if not k.startswith('_')},
        'logging': {k:v for k,v in vars(LOGGING_CONFIG).items() if not k.startswith('_')},
        'patch_analysis': {k:v for k,v in vars(PATCH_CONFIG).items() if not k.startswith('_')},
        'excel': {k:v for k,v in vars(EXCEL_CONFIG).items() if not k.startswith('_')},
        'remote': {k:v for k,v in vars(REMOTE_CONFIG).items() if not k.startswith('_')}
    }
    
    external_data = load_external_configs(json_path, yaml_path)
    final_config = merge_config(final_config, external_data)
    
    return final_config
