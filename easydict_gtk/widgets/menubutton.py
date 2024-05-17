from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, GObject, Adw

# internal imports
from settings import images
from .dialogs import SettingsDialog
import asyncio
import sys


class MenuButton(Gtk.MenuButton):
    """
    Wrapper class for at Gtk.Menubutton
    """

    def __init__(self, win):
        super(MenuButton, self).__init__()
        self.win = win
        opt_image = Gtk.Image.new_from_file(images["easydict-pref-icon.png"])
        opt_image.set_size_request(40, 40)
        self.set_child(opt_image)
        self.set_child_visible(True)
        self.create_actions_for_main_window()
        popover_menu = self.create_popover_menu()
        self.set_popover(popover_menu)

    def close_app(self):
        # closing the app we should do in three steps
        # 1 - close the loop in another Thread (not needed, but it is correct)
        async def loop_stop(loop):
            loop.stop()

        asyncio.run_coroutine_threadsafe(loop_stop(self.win._loop), self.win._loop)

        # 2 - close the db (definitely needed, without it the app will not close itself )
        asyncio.run(self.win.search.adb.close_db())

        # 3  - and close the app (its windows) itself
        self.win.close()
        # other possibilities how to close/destroy the app
        # self.win.destroy()
        # self.win = None

    def create_actions_for_main_window(self):
        # Create a new "Action for Settings button"
        action = Gio.SimpleAction.new("settings", None)
        action.connect("activate", lambda *args: self.create_settings_dialog())
        self.win.app.add_action(action)
        # Create a new "Action for Help button"
        action = Gio.SimpleAction.new("help", None)
        action.connect("activate", lambda *args: self.show_help_dialog())
        self.win.app.add_action(action)
        # Create a new "Action for About button"
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", lambda *args: self.show_about_dialog())
        self.win.app.add_action(action)
        # Create a new "Action for Quit button"
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", lambda *args: self.close_app())
        self.win.app.add_action(action)

    def create_settings_dialog(self):
        sd = SettingsDialog(self.win)
        sd()  # call this and show the Settings Dialog

    def create_popover_menu(self):
        popover = Gtk.PopoverMenu()
        menu = Gio.Menu.new()
        # add menu items with connected actions
        menu.append("Settings", "app.settings")
        menu.append("Help", "app.help")
        menu.append("About", "app.about")
        menu.append("Quit", "app.quit")
        popover.set_menu_model(menu)
        popover.set_has_arrow(True)
        return popover

    def show_help_dialog(self):
        text_buffer = Gtk.TextBuffer.new()
        with open(Path(__file__).parent.parent / "dict_data/help_eng.txt") as file:
            help_eng_text = file.read()

        text_buffer.set_text(help_eng_text)
        text_view = Gtk.TextView.new_with_buffer(text_buffer)
        text_view.set_vexpand(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_editable(False)
        sw = Gtk.ScrolledWindow()
        sw.set_child(text_view)
        frame = Gtk.Frame()
        frame.set_child(sw)
        help_dialog = Gtk.Dialog.new()
        help_dialog.set_transient_for(self.win)
        help_dialog.set_title("Help dialog")
        content_area = help_dialog.get_content_area()
        content_area.append(frame)
        help_dialog.set_size_request(800, 800)
        help_dialog.set_visible(True)

    def show_about_dialog(self):
        about = Gtk.AboutDialog()
        about.set_transient_for(
            self.win
        )  # Makes the dialog always appear in from of the parent window
        about.set_modal(
            self.win
        )  # Makes the parent window unresponsive while dialog is showing

        about.set_authors(["Jiří Němec - main developer", "Martin Mrňák - some tests"])
        about.set_copyright("Copyright 2023 Jiří Němec")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_website("https://easydict.jiri.one")
        about.set_website_label("https://easydict.jiri.one")
        about.set_version("0.5")
        about.set_artists(["Jiří Martin"])
        about.set_program_name("EasyDict-GTK")
        pixbuf_logo = GdkPixbuf.Pixbuf.new_from_file(images["easydict-icon.png"])
        logo = Gdk.Texture.new_for_pixbuf(pixbuf_logo)
        about.set_logo(logo)

        about.set_visible(True)

        # we can use Adw.AboutWindow (botton), but it is not so nice and it is harder to set logo
        # app = self.win.get_application()
        # dialog = Adw.AboutWindow(transient_for=app.get_active_window())
        # dialog.set_application_name=("EasyDict-GTK")
        # dialog.set_version("v0.5")
        # dialog.set_developer_name("Jiří Němec")
        # dialog.set_license_type(Gtk.License(Gtk.License.GPL_3_0))
        # dialog.set_comments("Adw about Window example")
        # dialog.set_website("https://easydict.jiri.one")
        # dialog.set_issue_url("https://github.com/jiri-one/easydict-gtk/issues")
        # dialog.set_artists(["Jiří Martin"])
        # dialog.add_credit_section("Contributors", ["Martin Mrňák - tests"])
        # dialog.set_copyright("© 2023 Jiří Němec")
        # dialog.set_developers(["Jiří Němec"])
        # dialog.set_application_icon("com.github.devname.appname") # icon must be uploaded in ~/.local/share/icons or /usr/share/icons

        # dialog.set_visible(True)
