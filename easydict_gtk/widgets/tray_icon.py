from easytray import get_dbus_backend, EasyTrayMenu, install_icon_to_xdg_data_home
from settings import images
from pathlib import Path

DBUS_PATH = "/SNIMenu"


class TrayIcon:
    def __init__(self, win):
        self.win = win
        self.tray = self.get_tray()
        self.menu = self.get_menu()

    def get_tray(self):
        icon_image = images["easydict-tray-icon.png"]
        icon_path = install_icon_to_xdg_data_home(Path(icon_image), 285)
        dbus_tray_backend = get_dbus_backend("dasbus")
        tray = dbus_tray_backend(
            category="ApplicationStatus",
            id=self.win.app.get_application_id(),
            title="First open source translator.",
            status="Active",
            icon="easydict-tray-icon",
            object_path=DBUS_PATH,
            icon_theme_path=icon_path,
            primary_callback=self.show_hide_window,
        )
        tray.create_tray_icon()
        return tray

    def show_hide_window(self, x, y):
        if self.win.props.visible:
            self.win.hide()
        else:
            self.win.show()

    def menu_buttons_catcher(self, action, target):
        button_label = action.property_get("label")
        # print(f"The button {button_label} was pressed.")

    def get_menu(self):
        menu = EasyTrayMenu(
            menu_items={
                "Settings": lambda *args: self.win.activate_action("app.settings"),
                "Help": lambda *args: self.win.activate_action("app.help"),
                "About": lambda *args: self.win.activate_action("app.about"),
                "Quit": lambda *args: self.win.activate_action("app.quit"),
            },
            dbus_path=DBUS_PATH,
        )
        menu.create_dbus_menu()
        return menu
