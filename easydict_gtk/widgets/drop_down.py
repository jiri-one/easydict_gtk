import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, GObject, Adw

# internal imports
from settings import images, ed_setup, LANGUAGES_DATA as lng_data


class Item_LngAndFlag(GObject.GObject):
    """Custom data element for a ListStore (Must be based on GObject)"""

    def __init__(self, id: int, language: str, flag_file: str):
        super().__init__()
        self.id = id
        self.language = language
        self.flag_file = flag_file


class LanguageDropdown(Gtk.DropDown):
    """Custom List for DropDown menu with flags"""

    def __init__(self):
        super().__init__()
        self.list_store = Gio.ListStore.new(item_type=Item_LngAndFlag)
        self.setup_content_for_store()
        self.set_model(self.list_store)
        factory = Gtk.SignalListItemFactory()
        self.set_factory(factory)
        factory.connect("setup", self.factory_setup)
        factory.connect("bind", self.factory_bind)
        # apply the settings
        self.apply_settings()

    def setup_content_for_store(self):
        for lng in lng_data.values():
            id = lng["id"]
            language = lng["label"]
            flag = lng["flag_file"]
            self.list_store.append(Item_LngAndFlag(id, language, flag))

    def factory_setup(self, factory, item: Gtk.ListItem):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        img = Gtk.Image()
        img.set_size_request(30, 30)
        label = Gtk.Label()
        box.append(label)
        box.append(img)
        item.set_child(box)

    def factory_bind(self, factory, item: Gtk.ListItem):
        box: Gtk.Box = item.get_child()
        item_data: Item_LngAndFlag = item.get_item()
        label = box.get_first_child()
        label.set_label(item_data.language)
        label.set_margin_end(10)
        img = box.get_last_child()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(images[item_data.flag_file])
        img.set_from_pixbuf(pixbuf)

    def apply_settings(self):
        lng = ed_setup.search_language
        lng_id = lng_data[lng]["id"]
        self.set_selected(lng_id)
        assert self.get_selected() == lng_id