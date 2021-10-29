# -*- coding: utf-8 -*-
# Standard
import os
import re
import traceback

# Third party
from Qt import QtCore, QtWidgets

from core_pipeline.utils import path_utils


def get_top_level_widgets(class_name=None, object_name=None):
    """
    Get existing widgets for a given class name

    Args:
        class_name (str): Name of class to search top level widgets for
        object_name (str): Qt object name

    Returns:
        List of QWidgets
    """
    matches = []

    # Find top level widgets matching class name
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            # Matching class
            if class_name and widget.metaObject().className() == class_name:
                matches.append(widget)
            # Matching object name
            elif object_name and widget.objectName() == object_name:
                matches.append(widget)
        # Error: 'PySide2.QtWidgets.QListWidgetItem' object
        #        has no attribute 'inherits'
        except AttributeError:
            continue
        # Print unhandled to the shell
        except Exception:
            traceback.print_exc()

    return matches


def close_existing(class_name=None, object_name=None):
    """
    Close and delete any existing windows of class_name

    Args:
        class_name (str): QtWidget class name
        object_name (str): Qt object name

    Returns: None
    """
    for widget in get_top_level_widgets(class_name, object_name):
        # Close
        widget.close()
        # Delete
        widget.deleteLater()


def space_to_underscore(widget):
    """
    Replace ' ' with '_' in line edit text
    """
    if not widget:
        return

    # Get current cursor position
    try:
        cursor_pos = widget.cursorPosition()
    except AttributeError:
        pass

    text = widget.text().replace(" ", "_")
    widget.setText(text)

    # Try to set cursor to original pos
    try:
        widget.setCursorPosition(cursor_pos)
    except AttributeError:
        pass


def load_hive_stylesheet():
    """
    Load hive stylesheet
    """
    css_file = path_utils.clean_path(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "config",
        "hive_stylesheet.css"
    ))
    with open(css_file, "r") as handle:
        return handle.read()


def create_button(text, tooltip=None, pad=None):
    """
    Create new button auto-resized to the display text

    Args:
        text (str): Display text for button
        tooltip (str): Tooltip str

    Returns:
        QtWidgets.QPushButton
    """
    try:
        text = str(text)
    # Unicode
    except Exception:
        text = text.encode("utf8")

    btn = QtWidgets.QPushButton(text)
    btn.setObjectName(text)
    btn.setContentsMargins(0, 0, 0, 0)
    if tooltip:
        btn.setToolTip(tooltip)

    # Focus policy
    btn.setFocusPolicy(QtCore.Qt.NoFocus)

    # Shrink to size
    auto_size(btn, pad=pad)

    return btn


def auto_size(widget, pad=None):
    """
    Resize widget to text size
    """
    # Shrink to size
    metrics = widget.fontMetrics()
    width = metrics.width(widget.text()) + 10

    if pad is not None:
        width += pad * 2

    widget.resize(width, widget.height())

    if pad is not None:
        widget.setContentsMargins(pad, 0, pad, 0)
