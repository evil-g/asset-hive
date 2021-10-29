# -*- coding: utf-8 -*-
# Standard
from functools import partial
import os
import re
import traceback

# Third party
from Qt import QtCore, QtGui, QtWidgets

# Package
from . import api, asset_info_widget, config, controller, widgets, utils
from hive_nuke_utils import nuke_ui


def show():
    """
    Show asset hive, parented under the main Nuke window
    """
    header = ["Asset", "Area", "Datatype", "Current Version",
              "Update Version", "File"]

    scene_controller = api.scene_interface.NukeScene()
    info_widget = asset_info_widget.NukeInfo(scene_controller)
    ui = AssetHiveWindow(scene_controller,
                         info_widget=info_widget,
                         header=header,
                         parent=nuke_ui.get_main_nuke_win())
    ui.show()
    return ui


class AssetHiveWindow(QtWidgets.QMainWindow):

    def __init__(self, scene_controller, info_widget=None,
                 default_preset="All Assets", open_dir_limit=5, header=None,
                 parent=None):
        """
        Initialize main ui
        """
        super(AssetHiveWindow, self).__init__(parent=parent)

        self.setWindowTitle("Asset Hive")

        # Stylesheet
        self.setStyleSheet(utils.style.load_hive_stylesheet())
        self.btn_color = QtGui.QColor(130, 204, 221)
        self.alert_yellow = QtGui.QColor(255, 211, 42)

        # Dir open limit
        self.open_dir_limit = open_dir_limit

        # Main layout
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()

        # -------------------------------------------------------
        # Button layout
        preset_layout = QtWidgets.QHBoxLayout()
        preset_layout.setSpacing(0)
        # Preset
        self.preset_label = QtWidgets.QLabel("Preset:")
        # Label
        self.preset_label.setMinimumWidth(45)
        preset_layout.addWidget(self.preset_label)
        # Dropdown
        self.preset_cmbx = QtWidgets.QComboBox()
        preset_layout.addWidget(
            self.preset_cmbx, QtWidgets.QSizePolicy.Expanding)
        self.preset_cmbx.setToolTip("Choose a filter preset")
        self.preset_cmbx.setStatusTip("Choose a filter preset")
        # Reload filter button
        self.preset_reload_btn = widgets.get_feather_button(
            "corner-up-left", self.btn_color)
        self.preset_reload_btn.setObjectName("feather")
        self.preset_reload_btn.setToolTip("Reload preset filters")
        self.preset_reload_btn.setStatusTip("Reload preset filters")
        self.preset_reload_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        preset_layout.addWidget(self.preset_reload_btn)
        # Save button
        self.preset_save_btn = widgets.get_feather_button(
            "save", self.btn_color)
        self.preset_save_btn.setObjectName("feather")
        self.preset_save_btn.setToolTip("Save preset")
        self.preset_save_btn.setStatusTip("Save preset")
        self.preset_save_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        preset_layout.addWidget(self.preset_save_btn)
        # Save new button
        self.preset_new_btn = widgets.get_feather_button(
            "plus-square", self.btn_color)
        self.preset_new_btn.setObjectName("feather")
        self.preset_new_btn.setToolTip("Save as new preset")
        self.preset_new_btn.setStatusTip("Save as new preset")
        self.preset_new_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        preset_layout.addWidget(self.preset_new_btn)
        self.main_layout.addLayout(preset_layout)

        # -------------------------------------------------------
        # Filter
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setAlignment(QtCore.Qt.AlignLeft)
        filter_layout.setSpacing(5)

        # Input
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setMinimumHeight(35)
        self.filter_edit.setMinimumWidth(200)
        self.filter_edit.setMaximumWidth(200)
        self.filter_edit.setObjectName("no_style")
        self.filter_edit.setPlaceholderText("Type a filter and press Enter")
        self.filter_edit.setStatusTip("To add a filter, type and press Enter")
        filter_layout.addWidget(
            self.filter_edit, QtWidgets.QSizePolicy.Expanding)

        # Filter display
        self.filter_tabs = QtWidgets.QTabWidget()
        self.filter_tabs.setObjectName("filters")
        self.filter_tabs.tabBar().setObjectName("filters")
        self.filter_tabs.setTabsClosable(True)
        self.filter_tabs.setMinimumHeight(35)
        self.filter_tabs.setMaximumHeight(35)
        self.filter_tabs.hide()
        filter_layout.addWidget(
            self.filter_tabs, QtWidgets.QSizePolicy.Expanding)
        self.main_layout.addLayout(filter_layout)

        # -------------------------------------------------------
        # Tabs setup
        asset_layout = QtWidgets.QHBoxLayout()
        # Asset tabs
        self.tab_bar = widgets.PlusTabBar()
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setTabBar(self.tab_bar)
        asset_layout.addWidget(self.tabs)
        # Info pane
        self.info_widget = info_widget
        asset_layout.addWidget(self.info_widget)
        self.main_layout.addLayout(asset_layout)

        # Tab buttons
        btn_widget = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(0)
        # Reload scene
        self.reload_btn = widgets.get_feather_button(
            "refresh-cw", self.btn_color)
        self.reload_btn.setObjectName("feather")
        self.reload_btn.setToolTip("Reload scene data")
        self.reload_btn.setStatusTip("Reload scene data")
        btn_layout.addWidget(self.reload_btn)
        # Copy filepath
        self.copy_btn = widgets.get_feather_button(
            "copy", self.btn_color)
        self.copy_btn.setObjectName("feather")
        self.copy_btn.setToolTip("Copy selected asset paths")
        self.copy_btn.setStatusTip("Copy selected asset paths")
        self.copy_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn_layout.addWidget(self.copy_btn)
        # Open directory
        self.open_dir_btn = widgets.get_feather_button(
            "folder", self.btn_color)
        self.open_dir_btn.setObjectName("feather")
        self.open_dir_btn.setToolTip("Open selected asset folder")
        self.open_dir_btn.setStatusTip("Open selected asset folder")
        self.open_dir_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn_layout.addWidget(self.open_dir_btn)
        # Focus mode
        self.focus_mode_btn = widgets.get_feather_button(
            "eye-off", self.btn_color)
        self.focus_mode_btn.setCheckable(True)
        self.focus_mode_btn.setObjectName("feather")
        self.focus_mode_btn.setToolTip("Focus mode")
        self.focus_mode_btn.setStatusTip(
            "Focus mode. Double click a row to focus the scene to that asset.")
        self.focus_mode_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn_layout.addWidget(self.focus_mode_btn)
        btn_widget.setLayout(btn_layout)
        self.tabs.setCornerWidget(btn_widget)

        # -------------------------------------------------------
        # Update buttons
        op_btn_layout = QtWidgets.QHBoxLayout()
        op_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.update_btn = QtWidgets.QPushButton("Update Scene")
        self.update_btn.setObjectName("operation")
        self.update_btn.setStatusTip("Update selected asset versions")
        op_btn_layout.addWidget(self.update_btn)
        self.main_layout.addLayout(op_btn_layout)

        # Tab notification tracking
        self.alert_icons = []

        # -------------------------------------------------------
        # Main layout
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        # -------------------------------------------------------
        # Init status bar
        self.setStatusBar(widgets.FlashStatusBar())

        # -------------------------------------------------------
        # Initial setup

        # Controller
        self.controller = controller.HiveUIControl(
            scene_controller, header=header, default_preset=default_preset)

        # Main tab (cannot be closed)
        self.add_tab(name=self.controller.default_preset)
        x_btn = self.tabs.tabBar().tabButton(0, QtWidgets.QTabBar.RightSide)
        x_btn.setEnabled(False)
        x_btn.resize(0, 0)

        # Load presets
        self.preset_cmbx.addItems(self.controller.preset_names())

        # -------------------------------------------------------
        # Connections
        self.controller.message.connect(self.statusBar().showMessage)
        self.controller.filter_added.connect(self._add_filter_tab)

        # Focus mode
        self.focus_mode_btn.toggled.connect(self.on_focus_mode_press)

        # Presets
        self.preset_cmbx.currentIndexChanged.connect(self.on_preset_changed)
        self.preset_reload_btn.pressed.connect(self.on_load_preset)

        # Filters
        self.filter_edit.returnPressed.connect(self.on_add_filter)
        self.filter_tabs.tabBar().tabCloseRequested.connect(
            self.on_remove_filter)

        # Tabs
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.tabBar().tabCloseRequested.connect(self.close_tab)
        self.tab_bar.plus_btn.pressed.connect(self.add_tab)
        self.tab_bar.tabBarDoubleClicked.connect(self.input_tab_name)

        # Asset table corner buttons
        self.reload_btn.pressed.connect(self.controller.load_scene_data)
        self.copy_btn.pressed.connect(self.on_copy_btn_press)
        self.open_dir_btn.pressed.connect(self.on_open_dir_press)

        # -------------------------------------------------------
        # Final setup

        # Load scene
        try:
            self.controller.load_scene_data()
        except Exception:
            traceback.print_exc()

        # Load first preset
        start_idx = self.preset_cmbx.findText(self.controller.default_preset)
        self.preset_cmbx.setCurrentIndex(start_idx)
        self.on_load_preset()

    def add_tab(self, name=None, preset=None):
        """
        Add new asset table tab

        Args:
            name (str): Name of new tab
            preset (str): Preset name for new tab
        """
        if not name:
            # Find largest index of tabs using default name
            tab_name = config.default_tab()
            current = [self.tabs.tabText(i) for i in range(self.tabs.count())
                       if self.tabs.tabText(i).startswith(tab_name)]
            idx = []
            for each in current:
                match = re.search(tab_name + "(?P<num>\d+$)", each)
                if match:
                    idx.append(int(match.group("num")))
            if idx:
                idx.sort()
                name = tab_name + str(idx[-1] + 1)
            else:
                name = tab_name + "1"

        # Create table widget
        asset_table = QtWidgets.QTableView()
        asset_table.setSortingEnabled(True)
        asset_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        asset_table.doubleClicked.connect(self.on_focus)
        if self.info_widget:
            asset_table.doubleClicked.connect(self.on_load_asset)
        self.tabs.addTab(asset_table, name)

        # Register with controller
        self.controller.add_view(
            asset_table, preset=self.controller.default_preset)

        # Focus to new tab
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

        # Init preset
        self.preset_cmbx.setCurrentIndex(
            self.preset_cmbx.findText(preset or self.controller.default_preset))
        # try:
        #     self.preset_cmbx.blockSignals(True)
        #     self.preset_cmbx.setCurrentIndex(
        #         self.preset_cmbx.findText(self.controller.default_preset))
        # finally:
        #     self.preset_cmbx.blockSignals(False)
        # # self.on_load_preset()

        # Connect view selection to control focus
        # asset_table.selectionModel().selectionChanged.connect(self.on_focus)

    def close_tab(self, index):
        """
        Close tab

        Args:
            index (int): Tab index
        """
        if 0 == index:
            return

        # print(self.tabs.tabText(index))
        self.controller.remove_view(index)
        self.tabs.removeTab(index)

    def input_tab_name(self, index):
        """
        Show line edit to rename tab

        Args:
            index (int): Tab index
        """
        if 0 == index:
            return

        # Position
        rect = self.tab_bar.tabRect(index)
        pos = rect.topLeft()
        pos.setY(pos.y())
        # Set up line edit
        edit = widgets.AutoCloseLineEdit(parent=self.tab_bar)
        edit.setText(self.tab_bar.tabData(index))
        edit.move(pos)
        # Closing text sets namespace
        edit.closing_text.connect(partial(self.set_tab_name, index))
        # Show
        edit.show()
        edit.resize(rect.width(), rect.height())
        edit.setFocus()

    def set_tab_name(self, index, name):
        """
        Validate and set tab name
        Cannot have 2 tabs of the same names. If a tab with the input name
        already exists, increase the '_#' suffix until it is unique.

        Args:
            index (int): Tab index
            name (str): New tab name
        """
        if name == self.tabs.tabText(index):
            return

        tab_names = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        idx = 1
        while name in tab_names:
            name = re.sub("(_|)\d*$", "_" + str(idx), name)
            idx += 1

            # Ok - tab is already the target name
            if name == self.tabs.tabText(index):
                return

        # Set name
        self.tabs.setTabText(index, name)

    def on_tab_changed(self, index):
        """
        Tab changed callback

        Args:
            index (int): Tab index
        """
        # Set to last tabs preset
        try:
            self.preset_cmbx.blockSignals(True)
            if self.controller.get_view_preset(index):
                self.preset_cmbx.setCurrentIndex(self.preset_cmbx.findText(
                    self.controller.get_view_preset(index)))
        finally:
            self.preset_cmbx.blockSignals(False)

        # Add filter tabs
        self.filter_tabs.clear()
        for filter in self.controller.get_filters(index, display=True):
            self._add_filter_tab(filter)

        # Refresh buttons
        self.refresh_preset_btns(index)
        self.refresh_tab_icons(index)

    def on_preset_changed(self, index):
        """
        Preset changed

        Args:
            index (int): Selected index
        """
        # Default tab is locked, cannot apply preset
        # Create new tab with preset applied
        if 0 == self.tabs.currentIndex():
            self.add_tab(preset=self.preset_cmbx.currentText())

        # # Test
        # # If tab does not a custom user name, make the preset name the tab name
        # current = self.tabs.tabText(self.tabs.currentIndex())
        # if config.is_default_tab(current) or config.is_preset_tab(current):
        #     self.set_tab_name(
        #         self.tabs.currentIndex(), self.preset_cmbx.currentText())

        self.on_load_preset()

    def on_load_preset(self):
        """
        Load preset filters
        """
        current_idx = self.tabs.currentIndex()

        # Clear existing filter
        self.filter_tabs.clear()

        # Load preset
        preset = self.preset_cmbx.currentText()
        self.controller.load_preset(preset, current_idx)

        # Refresh buttons
        self.refresh_preset_btns(current_idx)
        self.refresh_tab_icons(current_idx)

    def on_add_filter(self):
        """
        On filter add callback
        """
        filter = self.filter_edit.text()

        # No input filter
        if not filter:
            return

        # Current tab index
        current_idx = self.controller.get_view_index(self.tabs.currentWidget())

        # # Add new tab
        # if 0 == current_idx:
        #     self.on_preset_changed(current_idx)
        #     current_idx = self.controller.get_view_index(self.tabs.currentWidget())

        # Add filter
        self.controller.add_filter(filter, current_idx)

        # Clear for next filter
        self.filter_edit.setText("")

        # Refresh buttons
        self.refresh_preset_btns(current_idx)
        self.refresh_tab_icons(current_idx)

    def _add_filter_tab(self, filter, index=None):
        """
        Add filter tab
        """
        self.filter_tabs.show()

        wid = QtWidgets.QWidget()
        self.filter_tabs.addTab(wid, filter)
        wid.hide()
        wid.resize(0, 0)

        # Color preset filters
        try:
            filters = self.controller.get_preset_filters(
                self.preset_cmbx.currentText(), display=True)
        except KeyError:  # Invalid preset
            pass
        else:
            if filter in filters:
                self.filter_tabs.tabBar().setTabTextColor(
                    self.filter_tabs.count() - 1, self.alert_yellow)

    def on_remove_filter(self, index):
        """
        On filter remove callback
        """
        current_idx = self.controller.get_view_index(self.tabs.currentWidget())
        self.controller.remove_filter(self.filter_tabs.tabText(index),
                                      current_idx)
        self.filter_tabs.removeTab(index)

        # If there are no more filters, set preset to all
        if not self.controller.get_filters(current_idx):
            try:
                self.preset_cmbx.blockSignals(True)
                self.preset_cmbx.setCurrentIndex(
                    self.preset_cmbx.findText(self.controller.default_preset))
            finally:
                self.preset_cmbx.blockSignals(False)

        # Refresh buttons
        self.refresh_preset_btns(current_idx)
        self.refresh_tab_icons(current_idx)

    def on_copy_btn_press(self):
        """
        Copy file paths press callback
        """
        sel_model = self.tabs.currentWidget().selectionModel()
        indexes = sel_model.selectedIndexes()
        if indexes:
            files = []

            rows = []
            for index in indexes:
                if index.row() in rows:
                    continue
                files.append(self.tabs.currentWidget().model().index(
                    index.row(), 4).data()
                )
                rows.append(index.row())

            # Copy to clipboard
            clipboard = QtGui.QClipboard()
            clipboard.clear()
            clipboard.setText("\n".join(files))

            self.statusBar().showMessage(
                "Copied {0} asset paths to clipboard!".format(len(files)))
        else:
            self.statusBar().showMessage(
                "No assets selected. Clipboard is empty.")

    def on_open_dir_press(self):
        """
        Open asset folder button press callback
        """
        sel_model = self.tabs.currentWidget().selectionModel()
        indexes = sel_model.selectedIndexes()
        if indexes:
            dirs = []

            rows = []
            for index in indexes:
                if index.row() in rows:
                    continue
                dirs.append(
                    os.path.dirname(self.tabs.currentWidget().model().index(
                        index.row(), 4).data())
                )
                rows.append(index.row())

            # Double check with user
            if len(dirs) > self.open_dir_limit:
                msg = QtWidgets.QMessageBox(parent=self)
                msg.setText("Opening {0} asset directories may take a while."
                            "".format(len(dirs)))
                msg.setInformativeText("Do you want to continue?")
                msg.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                msg.setDefaultButton(QtWidgets.QMessageBox.No)
                if QtWidgets.QMessageBox.No == msg.exec_():
                    return

            self.statusBar().showMessage(
                "Opening {0} asset dirs...".format(len(dirs)))

            # Open
            for dir in dirs:
                utils.file_io.open_file_browser(dir)
        else:
            self.statusBar().showMessage(
                "No assets selected. Skipping directory open.")

    def on_focus(self, index):
        """
        Execute controller scene focus
        """
        # Focus scene
        if self.focus_mode_btn.isChecked():
            self.controller.focus_to_asset(index)

    def on_load_asset(self, index):
        """
        Load selected asset into info widget

        Args:
            index (QtCore.QModelIndex): Table model index
        """
        if self.info_widget:
            self.info_widget.load_asset(
                self.controller.get_asset(index.model().index(index.row(), 0)))

    def on_focus_mode_press(self):
        """
        Switch icon when focus mode button is pressed
        """
        name = "eye" if self.focus_mode_btn.isChecked() else "eye-off"
        icon = widgets.get_feather_icon(name, self.btn_color)
        self.focus_mode_btn.setIcon(icon)

    def refresh_preset_btns(self, index):
        """
        If all active filters are in the preset, enable save and new buttons.
        Otherwise, disable buttons.

        Args:
            index (int): Tab index
        """
        if self.controller.filters_match_preset(index):
            cond = False
        else:
            cond = True

        self.preset_save_btn.setEnabled(cond)
        self.preset_new_btn.setEnabled(cond)

    def refresh_tab_icons(self, index):
        """
        Refresh tab buttons
        """
        model = self.controller.views[index].model()
        alert_icon = self.tabs.tabBar().tabIcon(index)

        # Tab alert found
        if model.has_notification():
            if not alert_icon:
                alert_icon = widgets.get_feather_icon("alert-triangle",
                                                      self.alert_yellow)
                try:
                    self.alert_icons[index] = alert_icon
                except IndexError:
                    self.alert_icons.append(alert_icon)

                self.tabs.tabBar().setTabIcon(index, alert_icon)
        # No tab alert - clear Icon
        elif alert_icon:
            self.tabs.tabBar().setTabIcon(index, QtGui.QIcon())

    def show(self):
        """
        Show and load script data
        """
        super(AssetHiveWindow, self).show()
        self.resize(550, 500)

        # # Set up controller
        # self.controller.load_scene_data()

        # Set focus mode setting
        # self.focus_mode_btn.setChecked(True)
