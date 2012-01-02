import sys
try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import Qt
except ImportError:
    import sip
    for mod in ("QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"):
        sip.setapi(mod, 2)

    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import Qt


def find_menu_items(menu, _path = None):
    """Extracts items from a given Nuke menu

    Returns a list of strings, with the path to each item

    Ignores divider lines and hidden items (ones like "@;&CopyBranch" for shift+k)

    >>> found = find_menu_items(nuke.menu("Nodes"))
    >>> found.sort()
    >>> found[:5]
    ['/3D/Axis', '/3D/Camera', '/3D/CameraTracker', '/3D/DepthGenerator', '/3D/Geometry/Card']
    """
    import nuke

    if _path is None:
        _path = ""

    found = []

    mi = menu.items()
    for i in mi:
        if isinstance(i, nuke.Menu):
            # Sub-menu, recurse
            mname = i.name().replace("&", "")
            sub_found = find_menu_items(menu = i, _path = "%s/%s" % (_path, mname))
            found.extend(sub_found)
        elif isinstance(i, nuke.MenuItem):
            if i.name() == "":
                # Skip dividers
                continue
            if i.name().startswith("@;"):
                # Skip hidden items
                continue
            found.append("%s/%s" % (_path, i.name()))

    return found


def nonconsec_find(needle, haystack):
    """checks if each character of "needle" can be found in order (but not
    necessarily consecutivly) in haystack.
    For example, "mm" can be found in "matchmove", but not "move2d"
    "m2" can be found in "move2d", but not "matchmove"

    >>> nonconsec_find("m2", "move2d")
    True
    >>> nonconsec_find("m2", "matchmove")
    False

    Only checks after the last "/", unless needle contains "/" in
    which case the entire string is checked:

    >>> nonconsec_find("aa", "aa/bb")
    False
    >>> nonconsec_find("bb", "aa/bb")
    True
    >>> nonconsec_find("a/", "aa/bb")
    True
    """

    if "/" not in needle:
        haystack = haystack.split("/")[-1]

    # Turn haystack into list of characters (as strings are immutable)
    haystack = [hay for hay in str(haystack)]

    for needle_atom in needle:
        try:
            needle_pos = haystack.index(needle_atom)
        except ValueError:
            return False
        else:
            # Dont find string in same pos or backwards again
            del haystack[:needle_pos + 1]
    return True


class NodeWeights(object):
    def __init__(self, fname = None):
        self.fname = fname
        self.weights = {}

    def load(self):
        raise NotImplementedError("TODO") #TODO: Implement this

    def save(self):
        raise NotImplementedError("TODO") #TODO: Implement this

    def get(self, k, default = 0):
        if len(self.weights.values()) == 0:
            maxval = 1.0
        else:
            maxval = max(self.weights.values())
            maxval = min(1, maxval)
            maxval = float(maxval)
        return self.weights.get(k, default) / maxval

    def increment(self, key):
        self.weights.setdefault(key, 0)
        self.weights[key] += 1


class NodeModel(QtCore.QAbstractListModel):
    def __init__(self, mlist, weights, num_items = 20, filtertext = ""):
        super(NodeModel, self).__init__()

        self.weights = weights
        self.num_items = num_items

        self._all = mlist
        self._filtertext = filtertext
        self.update()

    def set_filter(self, filtertext):
        self._filtertext = filtertext
        self.update()

    def update(self):
        filtered = [x for x in self._all
                    if nonconsec_find(self._filtertext.lower().replace(" ", "/"), x.lower())]

        scored = [{'text': k, 'score': self.weights.get(k)} for k in filtered]

        # Store based on scores (descending), then alphabetically
        s = sorted(scored, key = lambda k: (-k['score'], k['text']))

        self._items = s
        self.modelReset.emit()

    def rowCount(self, parent = QtCore.QModelIndex()):
        return min(self.num_items, len(self._items))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # Return text to display
            raw = self._items[index.row()]['text']
            return raw

            """
            # To mirror Nuke's default thing, but need to rework search:
            value = raw.rpartition("/")
            return "%s [%s]" % (value[2], value[0])
            """

        elif role == Qt.DecorationRole:
            weight = self._items[index.row()]['score']

            hue = 0.4
            sat = weight ** 2 # gamma saturation to make faster falloff

            sat = min(1.0, sat)

            if index.row() % 2 == 0:
                col = QtGui.QColor.fromHsvF(hue, sat, 0.9)
            else:
                col = QtGui.QColor.fromHsvF(hue, sat, 0.8)

            pix = QtGui.QPixmap(12, 12)
            pix.fill(col)
            return pix

        elif role == Qt.BackgroundRole:
            return
            weight = self._items[index.row()]['score']

            hue = 0.4
            sat = weight ** 2 # gamma saturation to make faster falloff

            sat = min(1.0, sat)

            if index.row() % 2 == 0:
                return QtGui.QColor.fromHsvF(hue, sat, 0.9)
            else:
                return QtGui.QColor.fromHsvF(hue, sat, 0.8)
        else:
            # Ignore other roles
            return None


class TabyLineEdit(QtGui.QLineEdit):
    def event(self, event):
        """Make tab trigger returnPressed
        """

        #is_keypress = event.type() == QtCore.QEvent.Type.KeyPress
        is_keypress = event.type() == QtCore.QEvent.KeyPress

        if is_keypress and event.key() == QtCore.Qt.Key_Tab:
            # Can't access tab key in keyPressedEvent
            self.returnPressed.emit()
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Up:
            # These could be done in keyPressedEvent, but.. this is already here
            print "up"
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Down:
            print "Down"
            return True
        elif is_keypress and event.key() == QtCore.Qt.Key_Escape:
            # TODO: Emit custom signal maybe?
            self.parent().close()
            return True

        return super(TabyLineEdit, self).event(event)


class TabTabTabWidget(QtGui.QWidget):
    def __init__(self, on_create = None, parent = None, winflags = None):
        super(TabTabTabWidget, self).__init__(parent = parent)
        if winflags is not None:
            self.setWindowFlags(winflags)

        self.setMinimumSize(200, 300)
        self.setMaximumSize(200, 300)

        # Store callback
        self.cb_on_create = on_create

        # Input box
        self.input = TabyLineEdit()

        # Node weighting
        self.weights = NodeWeights("/tmp/weights.json")

        try:
            import nuke
            nodes = find_menu_items(nuke.menu("Nodes"))
        except ImportError:
            # FIXME: For testing outside Nuke, should be refactored
            import data_test
            nodes = data_test.menu_items

        # List of stuff, and associated model
        self.things_model = NodeModel(nodes, weights = self.weights)
        self.things = QtGui.QListView()
        self.things.setModel(self.things_model)

        # Add input and items to layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.things)

        # Remove margins
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Connect text change
        self.input.textChanged.connect(self.update)
        self.input.returnPressed.connect(self.create)

    def update(self, text):
        self.things.setCurrentIndex(self.things_model.index(0))
        self.things_model.set_filter(text)

    def create(self):
        selected = self.things.selectedIndexes()

        if len(selected) == 0:
            # Get first item
            selected = self.things_model.index(0)
        else:
            selected = selected[0]

        thing = selected.data()
        self.cb_on_create(name = thing)
        self.weights.increment(thing)


if __name__ == '__main__':
    try:
        # For testing outside Nuke
        app = QtGui.QApplication(sys.argv)
    except RuntimeError:
        app = None

    def on_create(name):
        try:
            import nuke
            m = nuke.menu("Nodes")
            mitem = m.findItem(name.lstrip("/")) # FIXME: Mismatch caused by find_menu_items
            mitem.invoke()
        except ImportError:
            pass

    t = TabTabTabWidget(on_create = on_create)
    t.show()
    t.raise_()

    if app is not None:
        app.exec_()
