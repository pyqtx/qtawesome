
import sys

from qtpy import QtCore, QtGui, QtWidgets

import qtawesome


# TODO: Set icon colour and copy code with color kwarg

DEFAULT_VIEW_COLUMNS = 10
AUTO_SEARCH_TIMEOUT = 500
ALL_COLLECTIONS = 'All'


class IconBrowser(QtWidgets.QMainWindow):
    """
    A small browser window that allows the user to search through all icons from
    the available version of QtAwesome.  You can also copy the name and python
    code for the currently selected icon.
    """

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.setWindowTitle('QtAwesome Icon Browser')

        self.settings = QtCore.QSettings("QtAwesome", "qta-browser")
        last_col = int(self.settings.value("view_columns", DEFAULT_VIEW_COLUMNS))
        last_style = self.settings.value("style", 0)

        qtawesome._instance()
        fontMaps = qtawesome._resource['iconic'].charmap

        iconNames = []
        for fontCollection, fontData in fontMaps.items():
            for iconName in fontData:
                iconNames.append('%s.%s' % (fontCollection, iconName))

        self._filterTimer = QtCore.QTimer(self)
        self._filterTimer.setSingleShot(True)
        self._filterTimer.setInterval(AUTO_SEARCH_TIMEOUT)
        self._filterTimer.timeout.connect(self._updateFilter)

        model = IconModel()
        model.setStringList(sorted(iconNames))

        self._proxyModel = QtCore.QSortFilterProxyModel()
        self._proxyModel.setSourceModel(model)
        self._proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self._listView = IconListView(self, last_col)
        self._listView.setUniformItemSizes(True)
        self._listView.setViewMode(QtWidgets.QListView.IconMode)
        self._listView.setModel(self._proxyModel)
        self._listView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._listView.doubleClicked.connect(self._copyIconText)
        self._listView.selectionModel().selectionChanged.connect(self._updateNameField)

        self._lineEdit = QtWidgets.QLineEdit(self)
        self._lineEdit.setAlignment(QtCore.Qt.AlignLeft)
        self._lineEdit.textChanged.connect(self._triggerDelayedUpdate)
        self._lineEdit.returnPressed.connect(self._triggerImmediateUpdate)

        self._comboBox = QtWidgets.QComboBox(self)
        self._comboBox.setMinimumWidth(75)
        self._comboBox.currentIndexChanged.connect(self._triggerImmediateUpdate)
        self._comboBox.addItems([ALL_COLLECTIONS] + sorted(fontMaps.keys()))

        lyt = QtWidgets.QHBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.addWidget(self._comboBox)
        lyt.addWidget(self._lineEdit)
        self._combo_style = QtWidgets.QComboBox(self)
        self._combo_style.addItem(qtawesome.styles.DEFAULT_DARK_PALETTE, 0)
        self._combo_style.addItem(qtawesome.styles.DEFAULT_LIGHT_PALETTE, 1)
        self._combo_style.setCurrentIndex(self._combo_style.findData(last_style))
        self._combo_style.currentTextChanged.connect(self._updateStyle)
        lyt.addWidget(self._combo_style)


        self._combo_cols = QtWidgets.QComboBox(self)
        for idx, no in enumerate([5, 10, 15, 20, 25, 30]):
            self._combo_cols.addItem(str(no), no)
        self._combo_cols.setCurrentIndex(self._combo_cols.findData(last_col))
        lyt.addWidget(self._combo_cols)
        self._combo_cols.currentTextChanged.connect(self._updateColumns)

        searchBarFrame = QtWidgets.QFrame(self)
        searchBarFrame.setLayout(lyt)

        self._nameField = QtWidgets.QLineEdit(self)
        self._nameField.setAlignment(QtCore.Qt.AlignCenter)
        self._nameField.setReadOnly(True)

        self._copyButton = QtWidgets.QPushButton('Copy Name', self)
        self._copyButton.clicked.connect(self._copyIconText)

        lyt = QtWidgets.QVBoxLayout()
        lyt.addWidget(searchBarFrame)
        lyt.addWidget(self._listView)
        lyt.addWidget(self._nameField)
        lyt.addWidget(self._copyButton)

        frame = QtWidgets.QFrame(self)
        frame.setLayout(lyt)

        self.setCentralWidget(frame)

        self.setTabOrder(self._comboBox, self._lineEdit)
        self.setTabOrder(self._lineEdit, self._combo_style)
        self.setTabOrder(self._combo_style, self._listView)
        self.setTabOrder(self._listView, self._nameField)
        self.setTabOrder(self._nameField, self._copyButton)
        self.setTabOrder(self._copyButton, self._comboBox)

        QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Return),
            self,
            self._copyIconText,
        )
        QtWidgets.QShortcut(
            QtGui.QKeySequence("Ctrl+F"),
            self,
            self._lineEdit.setFocus,
        )

        self._lineEdit.setFocus()

        geo = self.geometry()

        # QApplication.desktop() has been removed in Qt 6.
        # Instead, QGuiApplication.screenAt(QPoint) is supported
        # in Qt 5.10 or later.
        try:
            screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
            centerPoint = screen.geometry().center()
        except AttributeError:
            desktop = QtWidgets.QApplication.desktop()
            screen = desktop.screenNumber(desktop.cursor().pos())
            centerPoint = desktop.screenGeometry(screen).center()

        geo.moveCenter(centerPoint)
        self.setGeometry(geo)
        self._updateStyle(self._combo_style.currentText())

    def _updateStyle(self, text: str):
        _app = QtWidgets.QApplication.instance()
        if text == qtawesome.styles.DEFAULT_DARK_PALETTE:
            qtawesome.reset_cache()
            qtawesome.dark(_app)
        else:
            qtawesome.reset_cache()
            qtawesome.light(_app)
        self.settings.setValue("style", self._combo_style.currentData())

    def _updateColumns(self):
        self._listView.set_cols(self._combo_cols.currentData())
        self.settings.setValue("view_columns", self._combo_cols.currentData())

    def _updateFilter(self):
        """
        Update the string used for filtering in the proxy model with the
        current text from the line edit.
        """
        reString = ""

        group = self._comboBox.currentText()
        if group != ALL_COLLECTIONS:
            reString += r"^%s\." % group

        searchTerm = self._lineEdit.text()
        if searchTerm:
            reString += ".*%s.*$" % searchTerm

        # QSortFilterProxyModel.setFilterRegExp has been removed in Qt 6.
        # Instead, QSortFilterProxyModel.setFilterRegularExpression is
        # supported in Qt 5.12 or later.
        try:
            self._proxyModel.setFilterRegularExpression(reString)
        except AttributeError:
            self._proxyModel.setFilterRegExp(reString)

    def _triggerDelayedUpdate(self):
        """
        Reset the timer used for committing the search term to the proxy model.
        """
        self._filterTimer.stop()
        self._filterTimer.start()

    def _triggerImmediateUpdate(self):
        """
        Stop the timer used for committing the search term and update the
        proxy model immediately.
        """
        self._filterTimer.stop()
        self._updateFilter()

    def _copyIconText(self):
        """
        Copy the name of the currently selected icon to the clipboard.
        """
        indexes = self._listView.selectedIndexes()
        if not indexes:
            return

        clipboard = QtWidgets.QApplication.instance().clipboard()
        clipboard.setText(indexes[0].data())

    def _updateNameField(self):
        """
        Update field to the name of the currently selected icon.
        """
        indexes = self._listView.selectedIndexes()
        if not indexes:
            self._nameField.setText("")
        else:
            self._nameField.setText(indexes[0].data())


class IconListView(QtWidgets.QListView):
    """
    A QListView that scales it's grid size to ensure the same number of
    columns are always drawn.
    """

    def __init__(self, parent, columns):
        super().__init__(parent)
        self._columns = columns
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

    def set_cols(self, cols):
        self._columns = cols
        self._calc_cols()

    def _calc_cols(self):
        """
        Re-implemented to re-calculate the grid size to provide scaling icons

        Parameters
        ----------
        event : QtCore.QEvent
        """
        width = self.viewport().width() - 30
        # The minus 30 above ensures we don't end up with an item width that
        # can't be drawn the expected number of times across the view without
        # being wrapped. Without this, the view can flicker during resize
        tileWidth = width / self._columns
        iconWidth = int(tileWidth * 0.8)
        # tileWidth needs to be an integer for setGridSize
        tileWidth = int(tileWidth)

        self.setGridSize(QtCore.QSize(tileWidth, tileWidth))
        self.setIconSize(QtCore.QSize(iconWidth, iconWidth))

    def resizeEvent(self, event):
        self._calc_cols()
        return super().resizeEvent(event)


class IconModel(QtCore.QStringListModel):

    def __init__(self):
        super().__init__()

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        """
        Re-implemented to return the icon for the current index.

        Parameters
        ----------
        index : QtCore.QModelIndex
        role : int

        Returns
        -------
        Any
        """
        if role == QtCore.Qt.DecorationRole:
            iconString = self.data(index, role=QtCore.Qt.DisplayRole)
            return qtawesome.icon(iconString)
        return super().data(index, role)


def run():
    """
    Start the IconBrowser and block until the process exits.
    """
    app = QtWidgets.QApplication([])
    qtawesome.dark(app)

    browser = IconBrowser()
    browser.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
