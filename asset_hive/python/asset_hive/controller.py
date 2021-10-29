# -*- coding: utf-8 -*-
# Third party
from Qt import QtCore

# Package
from . import config, model


# Globals
ALWAYS_NOTIFY = 0
NEVER_NOTIFY = 1
AUTO_UPDATE_AND_NOTIFY = 2


class HiveUIControl(QtCore.QObject):
    """
    Hive UI Controller. Manages presets and filters for each view.
    """
    message = QtCore.Signal(str)
    filter_added = QtCore.Signal(str, int)
    filter_removed = QtCore.Signal(str, int)
    filters_cleared = QtCore.Signal(int)

    def __init__(self, scene_controller, views=None, header=None,
                 default_preset="All Assets"):
        """
        Initialize controller

        Args:
            views (list): List of table widgets to connect to scene data model
        """
        super(HiveUIControl, self).__init__()

        # Scene controller
        self.scene_controller = scene_controller

        self.model = None
        self.views = []
        self.view_filters = []
        self.view_presets = []
        self.header = header or ["Asset", "Current Version", "Update Version",
                                 "Notify Mode", "File"]

        self.valid_modes = [
            ALWAYS_NOTIFY, NEVER_NOTIFY, AUTO_UPDATE_AND_NOTIFY
        ]

        # Presets
        self.default_preset = default_preset
        self.presets = config.get_presets()

        # Set up views
        if views:
            for view in views:
                self.add_view(view)

        # Connections
        self.scene_controller.asset_data_added.connect(self.add_asset_row)
        self.scene_controller.asset_removed.connect(self.remove_asset_row)

    def preset_names(self):
        """
        Get preset names
        """
        return [self.default_preset] + sorted(
            [p for p in self.presets.keys() if p != self.default_preset])

    def get_preset_filters(self, name, display=False):
        """
        Get preset filter list

        Args:
            name (str): Preset name
            display (bool): If True, return display names of any
                            custom filters. Defaults to False.

        Returns:
            List of filters (str or class)
        """
        if name not in self.presets:
            raise KeyError("Invalid preset name: {0}".format(name))

        filters = []
        if display:
            for filter in self.presets[name]:
                if config.is_str_filter(filter):
                    filters.append(filter)
                else:
                    filters.append(filter.display_name)

        return filters or self.presets[name]

    def filters_match_preset(self, index):
        """
        Return True if index's current filters match its preset filters
        """
        return set(self.get_view_preset(index)) == set(self.get_filters(index))

    def load_preset(self, preset, index):
        """
        Load preset at index

        Args:
            preset (str): Preset name
            index (int): View index
        """
        self.clear_filters(index)

        for filter in self.get_preset_filters(preset):
            self.add_filter(filter, index)

        self.set_view_preset(index, preset)

    def reset(self):
        """
        Reset controller
        """
        self.model = None
        self.views = []
        self.view_filters = []
        self.view_presets = []

        self.scene_controller.reload()

    def init_model(self):
        """
        Initialize base scene data model
        """
        # Create base model
        self.model = model.TableModel(controller=self, header=self.header)
        self.scene_controller.load_scene_assets()
        self.model.sort(0)

    def load_scene_data(self):
        """
        Load scene data. Create new model for all asset Nodes.
        """
        # Model
        self.init_model()

        # Set proxy source models
        for view in self.views:
            proxy = view.model()
            proxy.setSourceModel(self.model)

        self.message.emit("Scene load finished!")

    def add_view(self, view, preset=None):
        """
        Add view widget and connect to model

        Args:
            view (QWidget): Table view widget
            preset (str, optional): Preset name
        """
        if view in self.views:
            raise ValueError("View has already been registered")

        # Add view
        self.views.append(view)
        self.view_filters.append([])
        self.view_presets.append(preset)

        # Proxy model
        proxy_model = model.CustomSortProxyModel()
        proxy_model.setSourceModel(self.model)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        view.setModel(proxy_model)

    def remove_view(self, index):
        """
        Remove view at index

        Args:
            index (int): List index
        """
        try:
            self.views.pop(index)
            self.view_filters.pop(index)
            self.view_presets.pop(index)
        except IndexError:
            pass

    def get_view_index(self, widget):
        """
        Get index of widget

        Args:
            widget (QWidget): Target widget

        Returns:
            Index int
        """
        return self.views.index(widget)

    def set_view_preset(self, index, preset):
        """
        Set preset name for view at index

        Args:
            index (int): Widget index
            preset (str): Preset name
        """
        self.view_presets[index] = preset

    def get_view_preset(self, index):
        """
        Get preset for view at index

        Args:
            index (int): Widget index
        """
        return self.view_presets[index]

    def load_filters(self, index):
        """
        Load filter at index
        """
        # Update filter regex
        sort_model = self.views[index].model()

        str_filters = []
        for filter in self.view_filters[index]:
            # Update filter regex
            if isinstance(filter, str) or isinstance(filter, unicode):
                str_filters.append(str(filter))
            else:
                sort_model.add_custom_filter(filter)

        sort_model.setFilterRegExp("|".join(str_filters))

    def add_filter(self, filter, index):
        """
        Add filter

        Args:
            filter (str): Filter input
            index (int): Index of view being filtered
        """
        if filter in self.view_filters[index]:
            return

        self.view_filters[index].append(filter)
        sort_model = self.views[index].model()

        # Update filter regex
        if config.is_str_filter(filter):
            sort_model.setFilterRegExp("|".join(self.get_str_filters(index)))
            self.filter_added.emit(str(filter), index)
        else:
            sort_model.add_custom_filter(filter)
            self.filter_added.emit(str(filter().display_name), index)

    def remove_filter(self, filter, index):
        """
        Remove filter

        Args:
            filter (str): Filter to remove
            index (int): Index of view being filtered
        """
        # No filter match
        if filter not in self.view_filters[index]:
            return

        # Remove from view filters list
        to_remove = self.view_filters[index].index(filter)
        self.view_filters[index].pop(to_remove)

        # Remove from proxy model regex
        sort_model = self.views[index].model()
        if config.is_str_filter(filter):
            sort_model.setFilterRegExp("|".join(self.get_str_filters(index)))
            self.filter_removed.emit(str(filter), index)
        else:
            sort_model.remove_custom_filter(filter)
            self.filter_removed.emit(str(filter().display_name), index)

    def clear_filters(self, index):
        """
        Clear filter. If no filter is given, clear all filters

        Args:
            name (str, optional): Filter name to remove
        """
        # Reset filter list
        self.view_filters[index] = []

        # Reset proxy model filter
        self.views[index].model().clear_custom_filters()
        self.views[index].model().setFilterRegExp(None)

        self.filters_cleared.emit(index)

    def get_filters(self, index, display=False):
        """
        Get filters for the view at index

        Args:
            index (int): View index
            display (bool): If True, return display names of any
                            custom filters. Defaults to False.

        Returns:
            List of filter strs
        """
        filters = []
        if display:
            for filter in self.view_filters[index]:
                if config.is_str_filter(filter):
                    filters.append(filter)
                else:
                    filters.append(filter.display_name)

        return filters or self.view_filters[index]

    def get_str_filters(self, index):
        """
        Get str filters at index

        Args:
            index (int): View index

        Returns:
            List of filter strs
        """
        return [f for f in self.get_filters(index) if config.is_str_filter(f)]

    def get_custom_filters(self, index):
        """
        Get str filters at index

        Args:
            index (int): View index

        Returns:
            List of filter strs
        """
        return [f for f in self.get_filters(index)
                if f not in self.get_str_filters(index)]

    def add_asset_row(self, data):
        """
        Add new row for asset data

        Args:
            data (list): List of data entries for a model row
        """
        self.model.insertRows(0)
        for i in range(len(data)):
            self.model.setData(self.model.index(0, i), data[i])

    def remove_asset_row(self, row):
        """
        Remove asset

        Args:
            node (nuke.Node): Remove asset
        """
        if row < self.model.rowCount():
            self.model.removeRows(row)

    def get_asset(self, index):
        """
        Get asset associated with index
        """
        return self.scene_controller.get_asset_by_name(
            index.data(QtCore.Qt.DisplayRole))

    def focus_to_asset(self, index):
        """
        Use scene controller
        """
        asset = self.get_asset(index.model().index(index.row(), 0))
        self.scene_controller.focus_to_asset(asset)

    def on_asset_changed(self, asset):
        """
        Scene asset attribute was updated.
        In this case, our scene asset is a Nuke node.

        Args:
            asset (nuke.Node): Nuke node that was changed
        """
        # Needs to be hooked to knobChanged for name and file
        pass

    def on_asset_removed(self, asset):
        """
        Scene asset was removed.
        Delete asset data from table model.

        Args:
            asset (nuke.Node): Nuke node that was deleted
        """
        # on node deleted callback
        pass

    def on_notify_mode_changed(self, asset, mode):
        """
        Update status of asset notifications.
        Mode choices are
        """
        pass
