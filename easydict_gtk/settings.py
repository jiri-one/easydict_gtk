from pathlib import Path
from os import environ

# internal imports
from utils import get_xdg_config_home


# set current working directory
cwd = Path(__file__).parent
# dictionary with images
images = dict()
for img_path in (cwd / "images").iterdir():
    images[img_path.name] = str(img_path.resolve())


cfg_dir = get_xdg_config_home()  # set user config directory


class Settings:
    def initiate_settings(self):
        try:
            # get setting of clippboard scan from db and set it
            pref_clipboard_scan = prefdb.search(query["settings"] == "clipboard_scan")[
                0
            ]["value"]
            self.checkbutton_scan.props.active = pref_clipboard_scan
            # get setting of window size remembering from db and set it
            pref_win_size_remember = prefdb.search(
                query["settings"] == "win_size_remember"
            )[0]["value"]
            self.checkbutton_size.props.active = pref_win_size_remember
            # get the window size from db and set it
            window_width, window_height = prefdb.search(
                query["settings"] == "window_size"
            )[0]["value"]
            self.window.set_default_size(window_width, window_height)
            # get setting of search language from db and set it
            pref_search_language = prefdb.search(
                query["settings"] == "search_language"
            )[0]["value"]
            self.image_language.props.file = str(
                self.cwd_images / f"flag_{pref_search_language}.svg"
            )
            self.language = pref_search_language
            self.combobox_language.set_active_id(pref_search_language)
        except IndexError:
            self.create_default_settings()
        self.dialog_about.props.version = f"{easydict_gtk.__version__}"

    def write_setting(self, name, value):
        prefdb.update({"value": value}, where("settings") == name)

    def create_default_settings(self):
        # set default settings
        prefdb.upsert(
            {"settings": "search_language", "value": "eng"},
            query["settings"] == "search_language",
        )
        prefdb.upsert(
            {"settings": "clipboard_scan", "value": True},
            query["settings"] == "clipboard_scan",
        )
        prefdb.upsert(
            {"settings": "window_size", "value": [360, 640]},
            query["settings"] == "window_size",
        )
        prefdb.upsert(
            {"settings": "win_size_remember", "value": True},
            query["settings"] == "win_size_remember",
        )
        # after default values are set, call initiate_settings again
        self.initiate_settings()
