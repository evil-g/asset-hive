# -*- coding: utf-8 -*-
from Qt import QtCore


class TableModel(QtCore.QAbstractTableModel):

    def __init__(self, controller=None, header=None, parent=None):
        """
        Initialize table model
        """
        super(TableModel, self).__init__(parent=parent)

        self._data = []
        self._header = header or []

        self.controller = controller

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        Table rows
        """
        return len(self._data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        Table columns

        node name, current version, latest version, mode
        """
        return len(self._header)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        Index
        """
        if not (0 <= row < self.rowCount(parent) and
                0 <= column < self.columnCount(parent)):
            return QtCore.QModelIndex()

        try:
            return self.createIndex(row, column, self._data[row][column])
        except IndexError:  # Invalid
            import traceback
            traceback.print_exc()

        return QtCore.QModelIndex()

    def parent(self, index):
        """
        Parent index
        """
        return QtCore.QModelIndex()

    def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
        """
        Table header
        """
        if QtCore.Qt.DisplayRole != role:
            return

        if QtCore.Qt.Horizontal == orientation:
            return self._header[column]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Table data method
        """
        if not index.isValid():
            return

        if QtCore.Qt.DisplayRole == role:
            return self._data[index.row()][index.column()]

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """
        Table setData method
        """
        if QtCore.Qt.EditRole == role:
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def insertRows(self, row, rows=1, parent=QtCore.QModelIndex()):
        """
        Insert table rows
        """
        self.beginInsertRows(parent, row, row + rows - 1)

        for each in range(row, row + rows):
            self._data.insert(row, ["" for each in range(self.columnCount())])

        self.endInsertRows()

        return True

    def removeRows(self, row, rows=1, parent=QtCore.QModelIndex()):
        """
        Remove table rows
        """
        self.beginRemoveRows(parent, row, rows + 1)

        del self._data[row:row + rows]

        self.endRemoveRows()

        return True

    def flags(self, index):
        """
        Set flags for table columns

        Returns:
            List of Qt flag constants
        """
        if not index.isValid():
            return

        # First item is checkable
        if 0 == index.column():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
                QtCore.Qt.ItemIsUserCheckable

        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        """
        Sort the model contents based on the column index chosen

        Args:
            column (int): Column index
            order (Qt.SortOrder): Ascending, descending, etc
        """
        if not self._data:
            return

        if not 0 <= column < self.columnCount():
            raise ValueError("Invalid column: {0}".format(column))

        self.layoutAboutToBeChanged.emit()

        # Sort
        self._data.sort(key=lambda c: c[column])

        # Reverse for descending order
        if order == QtCore.Qt.DescendingOrder:
            self._data.reverse()

        self.layoutChanged.emit()


class CustomSortProxyModel(QtCore.QSortFilterProxyModel):
    """
    Custom proxy model. Support custom filters.
    """

    def __init__(self, parent=None):
        """
        Initialize model
        """
        super(CustomSortProxyModel, self).__init__(parent=parent)

        # Filter all columns
        self.setFilterKeyColumn(-1)

        # Custom filters
        self.custom_filters = []

    def on_filter_changed(self):
        """
        Custom filter changed callback
        Emit data changed for entire table
        """
        model = self.sourceModel()
        if model:
            model.dataChanged.emit(
                model.index(0, 0),
                model.index(model.rowCount() - 1, model.columnCount() - 1))

    def add_custom_filter(self, filter):
        """
        Add custom filter
        """
        if filter in self.custom_filters:
            return

        self.custom_filters.append(filter)
        self.on_filter_changed()

    def remove_custom_filter(self, filter):
        """
        Remove custom filter
        """
        self.custom_filters = [f for f in self.custom_filters
                               if f != filter]
        self.on_filter_changed()

    def clear_custom_filters(self):
        """
        Clear filter
        """
        self.custom_filters = []
        self.on_filter_changed()

    def has_notification(self):
        """
        Return True if model has any custom filter matches
        """
        if self.rowCount() and any([f.notify for f in self.custom_filters]):
            return True

        return False

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Filter acceptance override. In addition to typical regex filter,
        filter by relevant .

        Args:
            source_row (int): Source row
            source_parent (QModelIndex): Index

        Returns:
            True if filter accepts row
        """
        base_result = super(CustomSortProxyModel, self).filterAcceptsRow(
            source_row, source_parent)

        # If base class result is true, don't bother with custom filters
        if self.filterRegExp().pattern() and base_result:
            return True

        # Check custom filters
        src_model = self.sourceModel()
        controller = src_model.controller

        if self.custom_filters and controller:
            # Run each fiter
            # If a match is found, return immediately
            for filter in self.custom_filters:
                try:
                    index = src_model.index(source_row, 0, source_parent)
                    result = filter().accepts(controller.get_asset(index),
                                              proxy_model=self,
                                              source_row=source_row,
                                              source_parent=source_parent)
                except Exception:
                    raise
                else:
                    if result:
                        return True

            # No custom filters matched
            return False

        # No default or custom filters
        return base_result
