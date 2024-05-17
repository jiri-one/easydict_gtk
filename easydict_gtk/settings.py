from pathlib import Path
import configparser

# internal imports
from utils import get_xdg_config_home

DEFAULT_SETTINGS = {  # TODO: for any value we can add validator
    "win_size_remember": {"value": True, "type": bool},
    "win_height": {"value": 1200, "type": int},
    "win_width": {"value": 600, "type": int},
    "clipboard_scan": {"value": False, "type": bool},
    "search_language": {"value": "eng", "type": str},
    "tray_icon": {"value": False, "type": bool},
}

LANGUAGES_DATA = {
    "eng": {
        "id": 0,
        "label": "ENG",
        "name": "English",
        "native_name": "English",
        "flag_file": "flag_eng.svg",
    },
    "cze": {
        "id": 1,
        "label": "CZE",
        "name": "Czech",
        "native_name": "Česky",
        "flag_file": "flag_cze.svg",
    },
}

# set current working directory
cwd = Path(__file__).parent
# dictionary with images
images = dict()
for img_path in (cwd / "images").iterdir():
    images[img_path.name] = str(img_path.resolve())


cfg_dir = get_xdg_config_home()  # set user config directory
ini_file = cfg_dir / "easydict.ini"  # set user config file


class Settings:
    def __init__(self, ini_file):
        self.ini_file = ini_file
        self.config = configparser.ConfigParser()
        # check if ini_file exists and if not, create it
        if not ini_file.exists():
            self.config["EASYDICT"] = {
                key: value_and_type["value"]
                for key, value_and_type in DEFAULT_SETTINGS.items()
            }
            with open(ini_file, "w") as configfile:
                self.config.write(configfile)
        # read the ini file
        try:
            self.config.read(ini_file)
        except configparser.ParsingError as e:
            e.message = (
                "\n\nSomething went wrong, best solution is to delete this file and let EasyDict to create new one.\n\n"
                + e.message
            )
            raise

        try:
            self.ed_config = self.config["EASYDICT"]
        except KeyError:
            raise KeyError("In easydict.ini file has to be [EASYDICT] section!")

        for key, value_and_type in DEFAULT_SETTINGS.items():
            type_of_value = value_and_type["type"]
            default_value = value_and_type["value"]
            try:
                # get actual value from config file or get default value
                if type_of_value == bool:
                    # getboolean method is case insensitive and care about more variants
                    value = self.ed_config.getboolean(key, default_value)
                elif type_of_value == int:
                    value = self.ed_config.getint(key, default_value)
                else:  # value is string
                    value = self.ed_config.get(key, default_value)
            except ValueError as e:
                e.message = "\n\nSomething went wrong, you have been written bad value type for some key, best solution is to delete this file and let EasyDict to create new one.\n\n"
                raise
            # set all keys and values like this object attributes
            setattr(self, key, value)

    def __setattr__(self, attr_name, attr_value):
        super().__setattr__(attr_name, attr_value)
        if attr_name in DEFAULT_SETTINGS:
            self.ed_config[attr_name] = str(attr_value)
            with open(self.ini_file, "w") as configfile:
                self.config.write(configfile)

    def write_settings(self, attr, value):
        setattr(self, attr, value)


# this should be imported in other files/modules
ed_setup = Settings(ini_file)
