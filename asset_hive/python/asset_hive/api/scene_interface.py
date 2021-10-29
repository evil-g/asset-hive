# -*- coding: utf-8 -*-
# Third party
import nukescripts
from Qt import QtCore

# Pipeline
from hive_nuke_utils import node_utils, script_utils

# Anima pipeline
from core_pipeline import constant, path_manager


class BasicScene(QtCore.QObject):
    """
    Basic scene data interface.
    Subclass for DCC or pipeline specific functionality.
    """
    asset_added = QtCore.Signal(object)
    asset_removed = QtCore.Signal(object)

    asset_data_added = QtCore.Signal(list)

    def __init__(self):
        """"""
        super(BasicScene, self).__init__()

        self.assets = []

    def get_scene_assets(self):
        """
        Get assets in the current scene
        """
        raise NotImplementedError

    def get_asset_path(self, asset):
        """
        Get asset path
        """
        raise NotImplementedError


class NukeScene(BasicScene):
    """
    Nuke scene interface
    """
    def load_scene_assets(self):
        """
        Load scene assets
        """
        self.assets = []

        # Add asset for each knob
        scene_file_data = script_utils.get_script_filepaths()
        for node, files in scene_file_data.iteritems():
            for knob, path in files.iteritems():
                self.add_asset(node.knob(knob))

    def add_asset(self, asset):
        """
        Add knob asset

        Args:
            asset (nuke.File_Knob): Nuke file knob
        """
        if asset in self.assets:
            return

        self.assets.append(asset)
        self.asset_added.emit(asset)
        self.asset_data_added.emit(self.get_asset_data(asset))

    def get_asset_by_name(self, name):
        """
        Get nth asset in scene list

        Args:
            name (str): Asset name in model
        """
        for asset in self.assets:
            if name[:name.rfind(".")] == asset.node().fullName():
                return asset

    def get_latest_version(self, asset):
        """
        Get latest version

        Args:
            asset (nuke.File_Knob): Nuke file knob

        Returns:
            Version int
        """
        return node_utils.node_ops.get_latest_version(asset)

    def get_current_version(self, asset):
        """
        Get current version

        Args:
            asset (nuke.File_Knob): Nuke file knob

        Returns:
            Version int
        """
        ver_prefix, ver = nukescripts.version.version_get(asset.value(), "v")
        return int(ver)

    def get_asset_path(self, asset):
        """
        Get asset path

        Args:
            asset (nuke.File_Knob): Nuke file knob
        """
        return asset.value()

    def _get_asset_manager(self, asset):
        """
        Get asset path manager

        Args:
            asset (nuke.File_Knob): File knob

        Returns:
            PathManager
        """
        file = self.get_asset_path(asset)

        # Try image
        try:
            manager = path_manager.utils.get_image_manager(file)
        except Exception:
            # Try published file
            try:
                manager = path_manager.utils.get_pubfile_manager(file)
            except Exception:
                # Try work area image
                manager = path_manager.PathManager("work.render")
                manager.context_from_path(file)

        return manager

    def get_asset_datatype(self, asset):
        """
        Get asset datatype

        Args:
            asset (nuke.File_Knob): File knob

        Returns:
            Datatype str
        """
        manager = self._get_asset_manager(asset)
        return manager.get_context_var(constant.entities.DATATYPE)

    def get_asset_area(self, asset):
        """
        Get asset area

        Args:
            asset (nuke.File_Knob): File knob

        Returns:
            Area str
        """
        manager = self._get_asset_manager(asset)
        return manager.get_context_var(constant.entities.AREA)

    def get_asset_data(self, asset):
        """
        Get asset model data

        Args:
            asset (nuke.File_Knob): Nuke file knob

        Returns:
            List of model data
        """
        data = ["{0}.{1}".format(asset.node().fullName(), asset.name()),
                self.get_asset_area(asset),
                self.get_asset_datatype(asset),
                self.get_current_version(asset),
                self.get_latest_version(asset),
                self.get_asset_path(asset)]

        return data

    def get_asset(self, data):
        """
        Get asset data

        Args:
            data (list): Get asset whose data matches list

        Returns:
            nuke.File_Knob
        """
        for asset in self.assets:
            if self.get_asset_data(asset) == data:
                return asset

    def asset_index(self, asset):
        """
        Get asset index
        """
        pass

    def focus_to_asset(self, asset):
        """
        Show node properties pane

        Args:
            asset (nuke.File_Knob): Scene asset
        """
        # Show properties pane
        asset.node().showControlPanel()
        # Zoom node graph
        script_utils.select_and_zoom(asset.node())
