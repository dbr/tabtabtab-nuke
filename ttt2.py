import sys
import random
from PySide import QtCore, QtGui
from PySide.QtCore import Qt


def nonconsec_find(needle, haystack):
    """checks if each character of "needle" can be found in order (but not
    necessarily consecutivly) in haystack.
    For example, "mm" can be found in "matchmove", but not "move2d"
    "m2" can be found in "move2d", but not "matchmove"
    """
    # Turn haystack into list of characters (as strings are immutable)
    haystack = [hay for hay in str(haystack)]

    for needle_atom in needle:
        try:
            needle_pos = haystack.index(needle_atom)
        except ValueError:
            return False
        else:
            # Dont find string in same pos or backwards again
            del haystack[:needle_pos]
    return True


def get_bigrams(string):
    '''
    Takes a string and returns a list of bigrams
    '''
    s = string.lower()
    return [s[i:i+2] for i in xrange(len(s) - 1)]


def string_similarity(str1, str2):
    '''
    Perform bigram comparison between two strings
    and return a percentage match in decimal form

    http://stackoverflow.com/a/6859596
    '''
    pairs1 = get_bigrams(str1)
    pairs2 = get_bigrams(str2)
    union  = len(pairs1) + len(pairs2)
    hit_count = 0
    for x in pairs1:
        for y in pairs2:
            if x == y: hit_count += 1
    return (2.0 * hit_count) / union


def weighted_sort(x, y):
    x = x.lower()
    y = y.lower()
    x_w = ShakeNodeSelector.nodeWeights.get(x, 0)
    y_w = ShakeNodeSelector.nodeWeights.get(y, 0)

    if x_w > y_w:
        return -1
    elif y_w < x_w:
        return 1
    else:
        return cmp(x, y)


class NodeWeights(object):
    def __init__(self, fname = None):
        self.fname = fname
        self.weights = {}

    def load(self):
        raise NotImplementedError("TODO") #TODO: Implement this

    def save(self):
        raise NotImplementedError("TODO") #TODO: Implement this

    def increment(self, key):
        self.weights.setdefault(key, 0)
        self.weights[key] += 1


class NodeModel(QtCore.QAbstractListModel):
    def __init__(self, mlist, num_items = 20, filtertext = ""):
        super(NodeModel, self).__init__()

        self.num_items = num_items

        self._all = mlist
        self._filtertext = filtertext
        self.update()

    def set_filter(self, filtertext):
        self._filtertext = filtertext
        self.update()

    def update(self):
        if len(self._filtertext) == 0:
            # Blank filter text, alphanumeric sort
            s = sorted(self._all)[:10]
            self._items = [{'text': t, 'score': 0} for t in s[:10]]
        else:
            # Rank names based on user input
            ranked = [(k, string_similarity(k, self._filtertext)) for k in self._all]

            # Add node popularity to scores
            #ranked = [(k, s + self.weights.get(k, 0)) for (k, s) in ranked]

            # Get n most highly ranked
            s = sorted(ranked, key = lambda k: k[1])[-self.num_items:][::-1]

            # Back into dictionary for use in data() etc
            self._items = [{'text': t[0], 'score': t[1]} for t in s]

        #self._items = [x for x in self._all if nonconsec_find(self._filtertext, x)]
        self.modelReset.emit()

    def rowCount(self, parent = QtCore.QModelIndex()):
        return min(self.num_items, len(self._items))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # Return text to display
            return self._items[index.row()]['text']
        elif role == Qt.BackgroundRole:
            weight = self._items[index.row()]['score']

            hue = 0.4
            sat = weight ** 2 # gamma saturation to make faster falloff

            if index.row() % 2 == 0:
                return QtGui.QColor.fromHsvF(hue, sat, 0.9)
            else:
                return QtGui.QColor.fromHsvF(hue, sat, 0.8)
        else:
            # Ignore other roles
            return None


class TabTabTabWidget(QtGui.QWidget):
    def __init__(self, parent = None):
        super(TabTabTabWidget, self).__init__(parent = parent)

        self.setMinimumSize(200, 300)
        self.setMaximumSize(200, 300)

        # Input box
        self.input = QtGui.QLineEdit()


        words = [x.strip() for x in random.sample(open("/usr/share/dict/words").readlines(), 1000)]

        # List of stuff, and associated model
        self.things_model = NodeModel(words)
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

    def update(self, text):
        self.things_model.set_filter(text)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    t = TabTabTabWidget()
    t.show()
    t.raise_()
    app.exec_()
