"""
Widgets for EasyDict-GTK
"""
import asyncio
from abc import abstractmethod
from settings import images
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, GObject, Adw

# internal imports
from settings import ed_setup, LANGUAGES_DATA as lng_data
from .dialogs import SettingsDialog


class ListViewBase(Gtk.ListView):
    """ListView base class, it setup the basic factory, selection model & data model
    handlers must be overloaded & implemented in a sub class
    """

    def __init__(self, model_cls):
        super().__init__()
        # Use the signal Factory, so we can connect our own methods to setup
        self.factory = Gtk.SignalListItemFactory()
        # connect to Gtk.SignalListItemFactory signals
        # check https://docs.gtk.org/gtk4/class.SignalListItemFactory.html for details
        self.factory.connect("setup", self.on_factory_setup)
        self.factory.connect("bind", self.on_factory_bind)
        self.factory.connect("unbind", self.on_factory_unbind)
        self.factory.connect("teardown", self.on_factory_teardown)
        # Create data model, use our own class as elements
        self.set_factory(self.factory)
        self.store = self.setup_store(model_cls)
        # create a selection model containing our data model
        self.model = self.setup_model(self.store)
        self.model.connect("selection-changed", self.on_selection_changed)
        # set the selection model to the view
        self.set_model(self.model)

    def setup_model(self, store: Gio.ListModel) -> Gtk.SelectionModel:
        """Setup the selection model to use in Gtk.ListView
        Can be overloaded in subclass to use another Gtk.SelectModel model
        """
        return Gtk.SingleSelection.new(store)

    @abstractmethod
    def setup_store(self, model_cls) -> Gio.ListModel:
        """Setup the data model
        must be overloaded in subclass to use another Gio.ListModel
        """
        raise NotImplemented

    def add(self, elem):
        """add element to the data model"""
        self.store.append(elem)

    # Gtk.SignalListItemFactory signal callbacks
    # transfer to some some callback stubs, there can be overloaded in
    # a subclass.

    def on_factory_setup(self, widget, item: Gtk.ListItem):
        """GtkSignalListItemFactory::setup signal callback

        Setup the widgets to go into the ListView"""

        self.factory_setup(widget, item)

    def on_factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """GtkSignalListItemFactory::bind signal callback

        apply data from model to widgets set in setup"""
        self.factory_bind(widget, item)

    def on_factory_unbind(self, widget, item: Gtk.ListItem):
        """GtkSignalListItemFactory::unbind signal callback

        Undo the the binding done in ::bind if needed
        """
        self.factory_unbind(widget, item)

    def on_factory_teardown(self, widget, item: Gtk.ListItem):
        """GtkSignalListItemFactory::setup signal callback

        Undo the creation done in ::setup if needed
        """
        self.factory_teardown(widget, item)

    def on_selection_changed(self, widget, position, n_items):
        # get the current selection (GtkBitset)
        selection = widget.get_selection()
        # the the first value in the GtkBitset, that contain the index of the selection in the data model
        # as we use Gtk.SingleSelection, there can only be one ;-)
        ndx = selection.get_nth(0)
        self.selection_changed(widget, ndx)

    # --------------------> abstract callback methods <--------------------------------
    # Implement these methods in your subclass

    @abstractmethod
    def factory_setup(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """Setup the widgets to go into the ListView (Overload in subclass)"""
        pass

    @abstractmethod
    def factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """apply data from model to widgets set in setup (Overload in subclass)"""
        pass

    @abstractmethod
    def factory_unbind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        pass

    @abstractmethod
    def factory_teardown(self, widget: Gtk.ListView, item: Gtk.ListItem):
        pass

    @abstractmethod
    def selection_changed(self, widget, ndx):
        """trigged when selecting in listview is changed
        ndx: is the index in the data store model that is selected
        """
        pass


class ListViewStrings(ListViewBase):
    """Add ListView with only strings"""

    def __init__(self):
        super(ListViewStrings, self).__init__(Gtk.StringObject)

    def setup_store(self, model_cls) -> Gio.ListModel:
        """Setup the data model
        Can be overloaded in subclass to use another Gio.ListModel
        """
        return Gtk.StringList()


class ResultListViewStrings(ListViewStrings):
    """Custom ListView"""

    def __init__(self, win: Gtk.ApplicationWindow):
        # Init ListView with store model class.
        super(ResultListViewStrings, self).__init__()
        self.win = win
        self.set_vexpand(True)
        # put some data into the model
        # results = db_search("eng", "live", fulltext=False)
        # for row in results:
        #     self.add(f"""<b>{row["eng"]}</b>\n {row["cze"]}""")

    def factory_setup(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """Gtk.SignalListItemFactory::setup signal callback (overloaded from parent class)

        Handles the creation widgets to put in the ListView
        """
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_wrap(True)
        label.set_margin_start(10)
        item.set_child(label)

    def factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """Gtk.SignalListItemFactory::bind signal callback (overloaded from parent class)

        Handles adding data for the model to the widgets created in setup
        """
        # get the Gtk.Label
        label = item.get_child()
        # get the model item, connected to current ListItem
        data = item.get_item()
        # Update Gtk.Label with data from model item
        label.set_markup(data.get_string())

    def selection_changed(self, widget, ndx: int):
        """trigged when selecting in listview is changed"""
        # print("ZDEEEEEEEEEEE", self.win, widget, ndx)
        # markup = self.win._get_text_markup(
        #     f"Row {ndx} was selected ( {self.store[ndx].get_string()} )"
        # )
        # self.win.page4_label.set_markup(markup)
