# -*- coding: utf-8 -*-
# Third party
from Qt import QtCore, QtGui, QtWidgets

# Pipeline
from core_pipeline import constant


class HiveInfoWidget(QtWidgets.QWidget):
    """
    Info widget base class. Required methods: self.load_asset
    """
    def __init__(self, scene_controller, parent=None):
        """
        Initialize
        """
        super(HiveInfoWidget, self).__init__(parent=parent)

        self.scene_controller = scene_controller

    def load_asset(self, asset):
        """
        Load asset
        """
        raise NotImplementedError


class NukeInfo(HiveInfoWidget):

    def __init__(self, scene_controller, parent=None):

        super(NukeInfo, self).__init__(scene_controller, parent=parent)

        # Main layout setup
        self.main_lyt = QtWidgets.QVBoxLayout()
        self.main_lyt.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(self.main_lyt)

        # Name
        name_lyt = QtWidgets.QHBoxLayout()
        name_lyt.setContentsMargins(0, 0, 0, 0)
        self.name_label = QtWidgets.QLabel("Name:")
        self.name_label.setMinimumWidth(60)
        self.name_label.setMaximumWidth(60)
        name_lyt.addWidget(self.name_label)
        self.name_info = QtWidgets.QLabel()
        name_lyt.addWidget(self.name_info)
        self.main_lyt.addLayout(name_lyt)

        # Area
        area_lyt = QtWidgets.QHBoxLayout()
        area_lyt.setContentsMargins(0, 0, 0, 0)
        self.area_label = QtWidgets.QLabel("Area:")
        self.area_label.setMinimumWidth(60)
        self.area_label.setMaximumWidth(60)
        area_lyt.addWidget(self.area_label)
        self.area_info = QtWidgets.QLabel()
        area_lyt.addWidget(self.area_info)
        self.main_lyt.addLayout(area_lyt)

        # Context
        context_lyt = QtWidgets.QHBoxLayout()
        context_lyt.setContentsMargins(0, 0, 0, 0)
        self.context_label = QtWidgets.QLabel("Context:")
        self.context_label.setMinimumWidth(60)
        self.context_label.setMaximumWidth(60)
        context_lyt.addWidget(self.context_label)
        self.context_info = QtWidgets.QLabel()
        context_lyt.addWidget(self.context_info)
        self.main_lyt.addLayout(context_lyt)

        # Datatype
        datatype_lyt = QtWidgets.QHBoxLayout()
        datatype_lyt.setContentsMargins(0, 0, 0, 0)
        self.datatype_label = QtWidgets.QLabel("Datatype:")
        self.datatype_label.setMinimumWidth(60)
        self.datatype_label.setMaximumWidth(60)
        datatype_lyt.addWidget(self.datatype_label)
        self.datatype_info = QtWidgets.QLabel()
        datatype_lyt.addWidget(self.datatype_info)
        self.main_lyt.addLayout(datatype_lyt)

        # Layer
        layer_lyt = QtWidgets.QHBoxLayout()
        layer_lyt.setContentsMargins(0, 0, 0, 0)
        self.layer_label = QtWidgets.QLabel("Layer:")
        self.layer_label.setMinimumWidth(60)
        self.layer_label.setMaximumWidth(60)
        layer_lyt.addWidget(self.layer_label)
        self.layer_info = QtWidgets.QLabel()
        layer_lyt.addWidget(self.layer_info)
        self.main_lyt.addLayout(layer_lyt)

        # User
        user_lyt = QtWidgets.QHBoxLayout()
        user_lyt.setContentsMargins(0, 0, 0, 0)
        self.user_label = QtWidgets.QLabel("User:")
        self.user_label.setMinimumWidth(60)
        self.user_label.setMaximumWidth(60)
        user_lyt.addWidget(self.user_label)
        self.user_info = QtWidgets.QLabel()
        user_lyt.addWidget(self.user_info)
        self.main_lyt.addLayout(user_lyt)

    def load_asset(self, asset):
        """
        Load asset
        """
        self.name_info.setText(self.scene_controller.get_asset_name(asset))
        self.area_info.setText(self.scene_controller.get_asset_area(asset))

        manager = self.scene_controller._get_asset_manager(asset)
        # Context
        ctx_str = "{0}/{1}/{2}".format(
            manager.get_context_var(constant.entities.EPISODE),
            manager.get_context_var(constant.entities.SEQUENCE),
            manager.get_context_var(constant.entities.SHOT))
        self.context_info.setText(ctx_str)
        # Datatype
        self.datatype_info.setText(
            manager.get_context_var(constant.entities.DATATYPE))
        # Layer
        self.layer_info.setText(
            manager.get_context_var(constant.entities.LAYER))
        # User
        self.user_info.setText(
            manager.get_context_var(constant.entities.USER))
