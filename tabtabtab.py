try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import Qt
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import Qt



class AutoCompleteEdit(QtGui.QLineEdit):
    """
    Based on
    http://elentok.blogspot.com/2011/08/autocomplete-textbox-for-multiple.html
    """

    def __init__(self, model):
        super(AutoCompleteEdit, self).__init__()
        self._completer = QtGui.QCompleter(model)
        self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._completer.setWidget(self)
        self._completer.activated.connect(self._insertCompletion)

        self._keysToIgnore = [QtCore.Qt.Key_Enter,
                              QtCore.Qt.Key_Return,
                              #QtCore.Qt.Key_Escape,
                              QtCore.Qt.Key_Tab]

    def _insertCompletion(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        # Could potentially use self._completer.completionPrefix() to
        # append only the remained of the word, but it's more useful
        # to wipe all other text for this
        self.setText(completion)

    def textUnderCursor(self):
        text = self.text()
        i = self.cursorPosition()
        before = text[:i]
        #after = text[i:]
        return before

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in self._keysToIgnore:
                event.ignore()
                return

        super(AutoCompleteEdit, self).keyPressEvent(event)
        completionPrefix = self.textUnderCursor()

        if completionPrefix != self._completer.completionPrefix():
            self._updateCompleterPopupItems(completionPrefix)

        if len(event.text()) > 0 and len(completionPrefix) > 0:
            self._completer.complete()

        if len(completionPrefix) == 0:
            self._completer.popup().hide()


    def _updateCompleterPopupItems(self, completionPrefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(completionPrefix)
        self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0,0))



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


_widget = None
def nukedemo():
    global _widget

    import nuke
    values = find_menu_items(nuke.menu("Nodes"))

    hbox = QtGui.QHBoxLayout()

    print dir(hbox)
    #hbox.setSpacing(0)
    hbox.setContentsMargins(0, 0, 0, 0)

    editor = AutoCompleteEdit(values)
    hbox.addWidget(editor)

    window = QtGui.QWidget(None)#, Qt.FramelessWindowHint)
    window.setLayout(hbox)

    def yay(word):
        print "yay", word
        nuke.menu("Nodes").findItem(word.lstrip("/")).invoke()
        window.hide()
        window.destroy()

    editor._completer.activated.connect(yay)
    window.show()
    _widget = window


if __name__ == '__main__':
    def demo():
        import random
        values = [x.strip() for x in random.sample(open("/usr/share/dict/words").readlines(), 1000)]

        import sys
        app = QtGui.QApplication(sys.argv)
        editor = AutoCompleteEdit(values)

        window = QtGui.QWidget(None)#, Qt.FramelessWindowHint)

        def yay(word):
            print "yay", repr(word)
            editor.hide()

        editor._completer.activated.connect(yay)

        editor.show()
        editor.raise_()

        sys.exit(app.exec_())

    demo()
