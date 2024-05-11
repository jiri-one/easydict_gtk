import asyncio
from abc import abstractmethod
from settings import images
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, GObject, Adw

# internal imports
from backends.sqlite_backend import SQLiteBackend
from settings import ed_setup, LANGUAGES_DATA as lng_data
from .dialogs import SettingsDialog
from .drop_down import LanguageDropdown


class SearchBar(Gtk.SearchBar):
    """Wrapper for Gtk.Searchbar Gtk.SearchEntry"""

    def __init__(self, loop, win: Gtk.ApplicationWindow = None):
        super(SearchBar, self).__init__()
        self._loop = loop
        self.task = None
        self.search_type = "first_chars"
        self.win = win
        search_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_box.add_css_class("ui/search_box.css")
        first_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        second_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # Add SearchEntry
        self.entry = Gtk.SearchEntry()
        self.entry.set_hexpand(True)
        self.entry.connect("changed", self.on_search)
        first_hbox.append(self.entry)
        # add Search button
        self.button = Gtk.Button(label="Search")
        # Add DropDown menu
        self.dropdown = LanguageDropdown()
        self.button.connect("clicked", self.on_search)
        # first_hbox.append(self.button)
        first_hbox.append(self.dropdown)

        # second line with toggle buttons
        self.toggle_first = Gtk.ToggleButton(label="First chars")
        self.toggle_first.set_active(True)
        self.toggle_whole_word = Gtk.ToggleButton(label="Whole word")
        self.toggle_whole_word.set_active(False)
        self.toggle_whole_word.set_group(self.toggle_first)
        self.toggle_fulltext = Gtk.ToggleButton(label="Fulltext")
        self.toggle_fulltext.set_active(False)
        self.toggle_fulltext.set_group(self.toggle_first)

        self.toggle_first.props.hexpand = True
        self.toggle_whole_word.props.hexpand = True
        self.toggle_fulltext.props.hexpand = True
        self.toggle_first.connect("clicked", self.on_toggle)
        self.toggle_whole_word.connect("clicked", self.on_toggle)
        self.toggle_fulltext.connect("clicked", self.on_toggle)

        second_hbox.append(self.toggle_first)
        second_hbox.append(self.toggle_whole_word)
        second_hbox.append(self.toggle_fulltext)

        search_box.append(first_hbox)
        search_box.append(second_hbox)
        self.set_child(search_box)
        # connect search entry to seach bar
        self.connect_entry(self.entry)
        if win:
            # set key capture from main window, it will show searchbar, when you start typing
            self.set_key_capture_widget(win)
        # show close button in search bar
        self.set_show_close_button(False)
        # Turn ON search mode
        self.set_search_mode(True)

        # initialization of async SQLiteBackend
        self.adb = SQLiteBackend()
        asyncio.run(self.adb.db_init())

    def show_new_results(self, result_strings=None):
        # and with results we need to update the ListViewString store - it is StringList
        store = self.win.listview_str.store
        # remove all search results from current store and add all results together (if there are any)
        store.splice(0, len(store), result_strings)
        # link to splice method: https://lazka.github.io/pgi-docs/Gtk-4.0/classes/StringList.html#Gtk.StringList.splice

    async def search_task(self, word, lng, search_type):
        # default language for results
        lng1 = lng
        # and second language for translation results
        lng2 = [lang for lang in ["cze", "eng"] if lang != lng1][0]

        result_strings = list()
        self.task = asyncio.create_task(self.adb.search_async(word, lng, search_type))
        results = await self.task
        if results:
            for item in results.items:
                if item.notes:
                    notes = " | " + item.notes
                else:
                    notes = ""
                if item.special:
                    special = " | " + item.special
                else:
                    special = ""
                whole_string = f"""<b>{getattr(item, lng1)}</b>\n {getattr(item, lng2)}{notes}{special}"""
                result_strings.append(whole_string)

        GLib.idle_add(self.show_new_results, result_strings)
        # links about GLib.idle_add
        # https://lazka.github.io/pgi-docs/#GLib-2.0/functions.html#GLib.idle_add
        # https://pygobject.readthedocs.io/en/latest/guide/threading.html

    async def search_in_db(self, word, lng, search_type):
        create_new_task = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                print(f"canceled: {self.task.cancelled()} or done: {self.task.done()}")
                self.task = None

            if self.task.cancelled() or self.task.done():
                create_new_task = True
        else:
            create_new_task = True
        # if we initiate new search task and search word is not empty
        if create_new_task and word != "":
            await self.search_task(word, lng, search_type)

        # elif the word is empty, so we will empty the listview
        elif create_new_task and word == "":
            GLib.idle_add(self.show_new_results)
            # links about GLib.idle_add
            # https://lazka.github.io/pgi-docs/#GLib-2.0/functions.html#GLib.idle_add
            # https://pygobject.readthedocs.io/en/latest/guide/threading.html

    def on_search(self, caller_obj):
        # get text from search entry
        word = self.entry.props.text
        # if we have word (searched text), then we need show the stack with results
        if word:
            if self.win.front_page in self.win.main_box:
                self.win.main_box.remove(self.win.front_page)
            if self.win.stack not in self.win.main_box:
                self.win.main_box.append(self.win.stack)
        else:  # if entry is empty, we will shof front page
            if self.win.stack in self.win.main_box:
                self.win.main_box.remove(self.win.stack)
            if self.win.front_page not in self.win.main_box:
                self.win.main_box.append(self.win.front_page)
            # store = self.win.listview_str.store
            # and remove all search results from current store
            # store.splice(0, len(store))
            # return None
        # get current language settings
        lng = self.dropdown.get_selected_item().language
        # get current search type
        search_type = self.search_type
        asyncio.run_coroutine_threadsafe(
            self.search_in_db(word, lng, search_type), self._loop
        )
        return None

    def on_toggle(self, button):
        # firsly we will get info about toggle button and set correct search type
        if button.props.label == "Fulltext":
            self.search_type = "fulltext"
        elif button.props.label == "Whole word":
            self.search_type = "whole_word"
        elif button.props.label == "First chars":
            self.search_type = "first_chars"
        else:
            raise ValueError(
                "Use only known toggles: 'Fulltext' or 'Whole word' or 'First chars'"
            )
        # and then we run search in db to sync toggle button state with results
        self.on_search(button)
