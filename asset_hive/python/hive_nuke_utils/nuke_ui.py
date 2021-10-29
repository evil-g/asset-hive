# -*- coding: utf-8 -*-
# Standard
import traceback

# Third party
import nuke
from Qt import QtWidgets


def get_main_nuke_win():
    """
    Get the main Nuke Qt window

    Returns:
        QWidget for Nuke main window
    """
    # Default main window registration
    main_win = "Foundry::UI::DockMainWindow"

    # Find top level widget with main window tag
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            if widget.inherits("QMainWindow") and \
                    widget.metaObject().className() == main_win:
                return widget
        # Error: 'PySide2.QtWidgets.QListWidgetItem' object
        #        has no attribute 'inherits'
        except AttributeError:
            continue
        # Print unhandled to the shell
        except Exception:
            nuke.tprint("Check for main window failed!")
            traceback.print_exc()
