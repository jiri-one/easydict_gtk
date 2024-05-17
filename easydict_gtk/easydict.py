"""
EasyDict-GTK - Python Gtk4 based Application
"""
import sys
import os
from pathlib import Path
import asyncio
from threading import Thread
from queue import Queue

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, GLib, GObject, Gio, Adw, Gdk

# internal imports
from settings import images, ed_setup
from widgets import ResultListViewStrings, SearchBar, FrontPage, MenuButton, TrayIcon


class MyWindow(Adw.ApplicationWindow):
    def __init__(self, title, loop, app, **kwargs):
        super().__init__(application=app)
        self.app = app
        self._loop = loop
        self.task = None
        self.tray = TrayIcon(win=self)
        self.connect("notify::default-width", self.on_size_changed)
        self.connect("notify::default-height", self.on_size_changed)
        # self.connect("close-request", self.on_close_button)
        self.load_css("ui/search_box.css")
        # set initial size of the window from settings
        self.set_default_size(ed_setup.win_width, ed_setup.win_height)
        self.set_title(title)
        self.main_box = Gtk.Box()
        self.main_box.props.orientation = Gtk.Orientation.VERTICAL
        title_label = Gtk.Label.new()
        title_label.set_justify(Gtk.Justification.CENTER)
        title_label.set_markup(
            "EasyDict-GTK\n<small>Completely open translator</small>"
        )
        header = Gtk.HeaderBar()
        header.set_title_widget(title_label)
        # Add Options button (Menu content is defined inside the MenuButton class)
        option_btn = MenuButton(self)
        header.pack_start(option_btn)
        header.set_decoration_layout("icon:minimize")
        self.search = SearchBar(loop, self)
        self.front_page = FrontPage()
        self.stack = Adw.ViewStack()
        self.main_box.append(header)
        self.main_box.append(self.search)
        self.main_box.append(self.front_page)
        content = self.setup_content()
        self.stack.add(content)
        self.set_content(self.main_box)
        # clipboard related settings
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        self.clipboard.connect("changed", self.on_clipboad_changed)

    def on_clipboad_changed(self, obj):
        # when the content of clipboard has changed, then we need to reread the content
        if self.props.visible:
            self.clipboard.read_text_async(None, self.on_paste_text)

    def on_paste_text(self, _clipboard, result):
        if ed_setup.clipboard_scan:
            # the content of the clipboard
            text = self.clipboard.read_text_finish(result)
            if self.search.entry.get_text().lower() != text.lower():
                self.search.entry.set_text(text)

    def setup_content(self):
        # Simple Listview with strings
        self.listview_str = ResultListViewStrings(self)
        lw_frame = Gtk.Frame()
        lw_frame.set_valign(Gtk.Align.FILL)
        lw_frame.set_vexpand(True)
        # lw_frame.set_margin_start(20)
        # lw_frame.set_margin_end(20)
        # lw_frame.set_margin_top(10)
        # lw_frame.set_margin_bottom(10)
        sw = Gtk.ScrolledWindow()
        # Create Gtk.Listview
        lw = self.listview_str
        sw.set_child(lw)
        lw_frame.set_child(sw)
        return lw_frame

    def load_css(self, css_fn):
        """create a provider for custom styling"""
        css_full_path = (Path(__file__).parent / css_fn).resolve()
        print(css_full_path, os.path.exists(css_full_path))
        if css_fn and os.path.exists(css_fn):
            css_provider = Gtk.CssProvider()
            try:
                css_provider.load_from_path(css_full_path)
            except GLib.Error as e:
                print(f"Error loading CSS : {e} ")
                return None
            print(f"loading custom styling : {css_fn}")
            self.css_provider = css_provider

    def write_windows_size_to_ini_file(self):
        # actual window size
        width = self.props.default_width
        height = self.props.default_height
        # write it to the disk with GLib.idle_add, because of another Thread
        GLib.idle_add(ed_setup.write_settings, "win_width", width)
        GLib.idle_add(ed_setup.write_settings, "win_height", height)

    async def save_win_size_after_one_sec(self):
        self.task = asyncio.create_task(asyncio.sleep(1))
        await self.task
        self.write_windows_size_to_ini_file()

    async def save_window_size(self):
        create_new_task = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                print(f"canceled: {self.task.cancelled()} or done: {self.task.done()}")
            if self.task.cancelled() or self.task.done():
                create_new_task = True
        else:
            create_new_task = True

        if create_new_task:
            await self.save_win_size_after_one_sec()

    def on_size_changed(self, widget, event):
        # if is "Remember window size?" checked in Settings dialog and event came from
        # "default-width" or "default-height", then we should save the windows size to the
        # file, but it is not good idea to write it directly with every change of window
        # size, so we will limit the number of writings with asyncio tasks, where we put
        # small time delay
        if ed_setup.win_size_remember:
            asyncio.run_coroutine_threadsafe(self.save_window_size(), self._loop)
            # we can save it directly, but better is to limit writing to the disk
            # ed_setup.write_settings("win_width", self.props.default_width)
            # ed_setup.write_settings("win_height", self.props.default_height)

    def on_close_button(self, widget):
        # this method is not used for now, we have button to minimize window
        self.hide()
        return True


class Application(Adw.Application):
    """Main Aplication class"""

    def __init__(self, loop):
        super().__init__(
            application_id="one.jiri.easydict-gtk",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self._loop = loop

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MyWindow("EasyDict-GTK", loop=self._loop, app=self)
        win.present()


def run_event_loop(q):
    """Run asyncio event loop in another Thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    q.put(loop)
    try:
        loop.run_forever()
    finally:
        loop.close()


def main(args=sys.argv[1:]):
    """Run the main application"""
    if "--reload" in args:
        import hupper

        package = Path(__file__).parent.parent
        sys.path.append(str(package))
        # start_reloader will only return in a monitored subprocess
        reloader = hupper.start_reloader("easydict_gtk.easydict.main")
        # monitor an extra file
        # reloader.watch_files(['foo.ini'])

    q = Queue()
    thread = Thread(target=run_event_loop, args=(q,))
    thread.daemon = True
    thread.start()
    loop = q.get()  # loop for search tasks and for save window size
    app = Application(loop)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
