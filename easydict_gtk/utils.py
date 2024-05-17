import difflib
import re
from os import environ
from pathlib import Path


def get_xdg_config_home() -> Path:
    xdg_config_home_str = environ.get("XDG_CONFIG_HOME")
    if xdg_config_home_str:
        xdg_config_home = Path(xdg_config_home_str)
    else:
        xdg_config_home = Path.home() / ".config"

    easydict_cfg_dir = xdg_config_home / "easydict"
    easydict_cfg_dir.mkdir(exist_ok=True)
    return easydict_cfg_dir
