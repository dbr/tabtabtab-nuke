"""Alternative "tab node creator thingy" for The Foundry's Nuke

https://github.com/dbr/tabtabtab-nuke
"""

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


def nonconsec_find(needle, haystack, anchored = False):
    """checks if each character of "needle" can be found in order (but not
    necessarily consecutivly) in haystack.
    For example, "mm" can be found in "matchmove", but not "move2d"
    "m2" can be found in "move2d", but not "matchmove"

    >>> nonconsec_find("m2", "move2d")
    True
    >>> nonconsec_find("m2", "matchmove")
    False

    Anchored ensures the first letter matches

    >>> nonconsec_find("atch", "matchmove", anchored = False)
    True
    >>> nonconsec_find("atch", "matchmove", anchored = True)
    False
    >>> nonconsec_find("match", "matchmove", anchored = True)
    True
    """

    if len(haystack) == 0 and len(needle) > 0:
        # "a" is not in ""
        return False

    elif len(needle) == 0 and len(haystack) > 0:
        # "" is in "blah"
        return True

    if "[" not in needle:
        haystack = haystack.rpartition(" [")[0]

    # Turn haystack into list of characters (as strings are immutable)
    haystack = [hay for hay in str(haystack)]

    if anchored:
        if needle[0] != haystack[0]:
            return False
        else:
            # First letter matches, remove it for further matches
            needle = needle[1:]
            del haystack[0]

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
        filtertext = self._filtertext.lower()

        # Two spaces as a shortcut for [
        filtertext = filtertext.replace("  ", "[")
        filtered = [x for x in self._all
                    if nonconsec_find(filtertext, x.lower(), anchored=True)]

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
    pressed_arrow = QtCore.Signal(str)

    def event(self, event):
        """Make tab trigger returnPressed
        """

        is_keypress = event.type() == QtCore.QEvent.KeyPress

        if is_keypress and event.key() == QtCore.Qt.Key_Tab:
            # Can't access tab key in keyPressedEvent
            self.returnPressed.emit()
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Up:
            # These could be done in keyPressedEvent, but.. this is already here
            self.pressed_arrow.emit("up")
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Down:
            self.pressed_arrow.emit("down")
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

        nodes = ["%s [%s]" % (n.rpartition("/")[2], n.rpartition("/")[0]) for n in nodes]

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

        # Update on text change
        self.input.textChanged.connect(self.update)

        # Reset selection on text change
        self.input.textChanged.connect(lambda: self.move_selection(where="first"))
        self.move_selection(where = "first") # Set initial selection

        # When enter/tab is pressed, create node
        self.input.returnPressed.connect(self.create)

        # Up and down arrow handling
        self.input.pressed_arrow.connect(self.move_selection)

    def move_selection(self, where):
        if where not in ["first", "up", "down"]:
            raise ValueError("where should be either 'first', 'up', 'down', not %r" % (
                    where))

        first = where == "first"
        up = where == "up"
        down = where == "down"

        if first:
            self.things.setCurrentIndex(self.things_model.index(0))
            return

        cur = self.things.currentIndex()
        if up:
            new = max(0, cur.row() - 1)
        elif down:
            new = min(self.things_model.rowCount(), cur.row() + 1)
        self.things.setCurrentIndex(self.things_model.index(new))

    def event(self, event):
        """Close when window becomes inactive (click outside of window)
        """
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.close()
            return True
        else:
            return super(TabTabTabWidget, self).event(event)

    def update(self, text):
        self.things.setCurrentIndex(self.things_model.index(0))
        self.things_model.set_filter(text)

    def close(self):
        """Clear current input when closing
        """
        self.input.setText("")
        super(TabTabTabWidget, self).close()

    def create(self):
        selected = self.things.selectedIndexes()

        if len(selected) > 0:
            # Get first selected item
            selected = selected[0]

        else:
            # Nothing selected, get first item
            selected = self.things_model.index(0)

        thing = selected.data()
        self.cb_on_create(name = thing)
        self.weights.increment(thing)
        self.close()


_tabtabtab_instance = None
def main():
    global _tabtabtab_instance

    if _tabtabtab_instance is not None:
        # TODO: Is there a better way of doing this? If a
        # TabTabTabWidget is instanced, it goes out of scope at end of
        # function and disappers instantly. This seems like a
        # reasonable "workaround"
        _tabtabtab_instance.show()
        return

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
            print "creating %s" % name

    t = TabTabTabWidget(on_create = on_create, winflags = Qt.FramelessWindowHint)
    t.show() #TODO: Make it appear under cursor like Nuke's tab thing does
    t.raise_()

    _tabtabtab_instance = t

    if app is not None:
        app.exec_()


if __name__ == '__main__':
    try:
        import nuke
        m_edit = nuke.menu("Nuke").findItem("Edit")
        m_edit.addCommand("Tabtabtab", main, "Tab")
    except ImportError:
        main()
