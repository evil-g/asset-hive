# -*- coding: utf-8 -*-
# Standard
import os
import re

# Third party
import nuke
import nukescripts
from Qt import QtWidgets

# Pipeline
from core_pipeline.utils import file_io
from core_pipeline_ui import utils
from . import node_utils


# Globals
WRITES = ["DeepWrite", "Write", "WriteGeo"]
READS = ["Read"]

# Licenses by tanker limit name
# {tanker_limit: node_class_prefix}
PLUGINS = {"rsmb": "OFXcom.revisionfx"}


def get_all_nodes(classes=None, groups=True):
    """
    Get all nodes matching the provided filters

    Args:
    Args:
        classes (str): List of Node class to filter by
        groups (bool): If True, get grouped nodes as well

    Returns:
        List of Nuke Nodes
    """
    all_nodes = nuke.allNodes(recurseGroups=groups)

    # Return matching classes
    if classes:
        matches = [n for n in all_nodes if n.Class() in classes]
        return sorted(matches, key=lambda f: f.fullName())

    # Return all nodes, sorted by full name
    return sorted(all_nodes, key=lambda f: f.fullName())


def get_camera_shakes():
    """
    Get all camera shake Transform nodes in the script

    Returns:
        List of Nuke Nodes
    """
    return [n for n in get_all_nodes("Transform")
            if node_utils.node_ops.get_anima_file_knob(n)]


def get_reads():
    """Get all Read nodes in this script"""
    return get_all_nodes(classes=READS)


def get_writes():
    """Get all Write nodes in this script"""
    return get_all_nodes(classes=WRITES)


def get_output_write():
    """
    Get the best output Write node for publishing, etc

    Write node N is chosen using the following precedence:
        1. N is the only Write node in the script
        2. N is the only selected Write node in the script
        3. N is the only enabled Write node in the script
        4. N is the only Write node left after disabled Writes
           and non-selected Writes are filtered out

    Raises: RuntimeError if node N can not be determined

    Returns:
        nuke.Node
    """
    writes = get_writes()

    # No write node
    if 0 == len(writes):
        raise RuntimeError("No Write node found!")
        # "Writeノードが見つかりません。"

    # Determine write node for publishing
    # Only 1 Write node
    if 1 == len(writes):
        return writes[0]
    # Multiple Write nodes
    else:
        # Selected writes
        sel_writes = [n for n in nuke.selectedNodes() if n in writes]
        # Enabled writes
        enabled = [n for n in writes if not n.knob("disable").value()]

        # 1 selected, enabled write
        if 1 == len(sel_writes) and sel_writes[0] in enabled:
            return sel_writes[0]
        # 1 enabled write
        elif 1 == len(enabled):
            return enabled[0]
        # More than one enabled - filter out by selection
        else:
            sel = [n for n in sel_writes if n in enabled]
            if not sel or len(sel) > 1:
                raise RuntimeError("Please select 1 Write node!")
                # "複数のWriteノードが見つかりました。 1を選択してください。"
            # 1 enabled Write in current selection
            return sel[0]


def get_dependencies(node, dep_list=None, filter=None):
    """
    Get all dependencies of given node

    Args:
        node (nuke.Node): Input node
        dep_list (list): List of dependecy Nodes
        filter (list): List of classes to filter by
                       If provided, only nodes matching
                       these classes will be added to the list

    Returns:
        List of nuke.Node dependencies
    """
    if not node:
        raise RuntimeError("Input node does not exist!")

    # Initialize dependency list
    if not dep_list:
        dep_list = []

    # Add node's dependencies
    deps = node.dependencies(
        nuke.EXPRESSIONS | nuke.INPUTS | nuke.HIDDEN_INPUTS)
    for dep in deps:
        # Add node to tracking list
        if dep not in dep_list:
            if filter and dep.Class() in filter:
                dep_list.append(dep)
            elif not filter:
                dep_list.append(dep)

            dep_list = get_dependencies(dep, dep_list=dep_list, filter=filter)

    return dep_list


def get_top_dependencies(node, dep_list=None, filter=None):
    """
    Get top-level dependencies for the provided node

    Args:
        node (nuke.Node): Input node
        dep_list (list): List of dependecy Nodes
        filter (list): List of classes to filter by
                       If provided, only nodes matching
                       these classes will be added to the list
        add (bool): If True, add to the current selection
                    If False, clear selection first

    """
    return [dep for dep in
            get_dependencies(node, dep_list=dep_list, filter=filter)
            if not dep.inputs()]


def select_dependencies(node, dep_list=None, filter=None, add=False):
    """
    Select all dependencies of given node

    Args:
        node (nuke.Node): Input node
        dep_list (list): List of dependecy Nodes
        filter (list): List of classes to filter by
                       If provided, only nodes matching
                       these classes will be added to the list
        add (bool): If True, add to the current selection
                    If False, clear selection first

    Returns:
        List of nuke.Node dependencies
    """
    # Clear selection
    if not add:
        nukescripts.clear_selection_recursive()

    nodes = get_dependencies(node, dep_list=dep_list, filter=filter)
    for node in nodes:
        if node.knob("selected"):
            node.knob("selected").setValue(True)


def get_script_filepaths(input_nodes=None, ignore=WRITES, class_filter=None):
    """
    Get all file nodes referenced by the current script

    Args:
        input_nodes (list): Nodes to collect file paths for.
                            If not provided, uses selected nodes.
                            If none selected, uses all nodes.
        ignore (list): List of Node classes to ignore
                       (Defaults to Write node classes)
        class_filter (list): Only collect these Node classes

    Note:

    Returns:
        Dict of node file data (format below)
        {nuke.Node: {File knob name: File path}}
    """
    if not input_nodes:
        input_nodes = nuke.selectedNodes() or get_all_nodes()

    files = {}
    for node in input_nodes:
        # Skip node if
        # 1. Class is in ignore list
        if ignore and node.Class() in ignore:
            continue
        # 2. Class filter is provided and class is not in it
        if class_filter and node.Class() not in class_filter:
            continue

        # Add Node file data
        node_files = node_utils.node_ops.get_node_files(node)
        if node_files:
            if node in files:
                files[node].update(node_files)
            else:
                files[node] = node_files

    return files


def get_script_frange():
    """
    Get start and end frame for a script
    """
    start = int(nuke.root().knob("first_frame").value())
    end = int(nuke.root().knob("last_frame").value())

    return start, end


def set_script_frange(start, end, fps, lock=None):
    """
    Set root node frame range values

    Args:
        start (int): Start frame
        end (int): End frame
        fps (float): Global FPS
        lock (bool, optional): If provided, set lock range
    """
    root = nuke.root()

    # Frange
    root.knob("first_frame").setValue(start)
    root.knob("last_frame").setValue(end)

    # Lock
    if lock is not None:
        root.knob("lock_range").setValue(lock)

    # FPS
    root.knob("fps").setValue(fps)


def find_format(res_x, res_y, name=""):
    """
    Find format

    Args:
        res_x (int): Resolution width
        res_y (int): Resolution height
        name (str, optional): If provided, make sure the name matches

    Returns:
        nuke.Format
    """
    for format in nuke.formats():
        if format.width() == res_x and format.height() == res_y:
            # If no name, or name is the format name, set it
            if not name or name == format.name():
                return format


def set_resolution(res_x, res_y, name=""):
    """
    Given res x and y, set root node format

    Args:
        res_x (int): Resolution width
        res_y (int): Resolution height
        name (str, optional): Resolution name

    Raises: ValueError if no match was found in the
            script's current formats

    Returns: None
    """
    format = find_format(res_x, res_y, name)

    # Set format
    if format:
        nuke.root().knob("format").setValue(format)
    # No match found, raise error
    else:
        raise ValueError(
            "Could not find format: {0} {1}x{2}".format(name, res_x, res_y))


def capture_viewer(filepath, qt=False, size=None):
    """
    Capture active viewer

    Args:
        filepath (str): Filepath to write
        qt (bool): If True, use Qt to capture instead of Nuke's
                   provided viewer capture. Defaults to False.
        size (QtCore.QSize): Size of Qt capture. Only used if qt=True.

    Raises: RuntimeError if there is no active viewer

    Returns: None
    """
    # Find Viewer to capture
    active_viewer = nuke.activeViewer()
    if not active_viewer:
        raise RuntimeError("No active Viewer. Failed to create thumbnail!")

    # No Viewer connected to active viewer panel
    viewer = active_viewer.node()
    if not viewer:
        raise RuntimeError("No active Viewer. Failed to create thumbnail!")

    file_io.make_dirs(os.path.dirname(filepath))

    # Capture viewer
    # Use qt
    if qt:
        viewer = active_viewer.node()
        widgets = [w for w in QtWidgets.QApplication.allWidgets()
                   if w.windowTitle() == viewer.fullName()]
        if widgets:
            size = size or widgets[0].size()
            try:
                utils.widgets.capture(
                    widgets[0], filepath, overwrite=True, size=size)
            # Bug on Linux in Qt-5.6.1 (PySide-2.0.0.alpha)
            # TypeError on 'PySide2.QtGui.QScreen.grabWindow' signature
            # Fixed in Qt-5.12.5
            # https://bugreports.qt.io/browse/PYSIDE-1063
            except TypeError:
                viewer.capture(filepath)
        # No viewer widget found - try Nuke
        else:
            viewer.capture(filepath)
    # Use Nuke
    else:
        viewer.capture(filepath)


def select_and_zoom(nodes, add=False):
    """
    Select and center zoom on the given nodes

    Args:
        nodes (list): Nodes to select + zoom
        add (bool): If True, add to current selection
                    If False, clear selection first
    """
    if not isinstance(nodes, list):
        nodes = [nodes]

    # TODO work with multiple nodes
    if len(nodes) > 1:
        raise ValueError("Unsupported. Only 1 node allowed in list")

    if not nodes:
        nodes = get_all_nodes()

    # Clear current selection
    if not add:
        nukescripts.clear_selection_recursive()

    for node in nodes:
        # Select
        node.knob("selected").setValue(True)

        # Center node
        x_zoom = node.xpos() + node.screenWidth() / 2
        y_zoom = node.ypos() + node.screenHeight() / 2
        nuke.zoom(2, [x_zoom, y_zoom])


def bottom_right_pos(nodes=None):
    """
    Get furthest bottom right position by a node

    Args:
        nodes (list of nuke.Node): List of nodes to compare
                                   Defaults to all ungrouped nodes

    Returns:
        x_pos, y_pos
    """
    nodes = nodes or get_all_nodes(groups=False)

    xpos = None
    ypos = None

    for node in nodes:
        if xpos is None:
            xpos = node.xpos()
        elif node.xpos() > xpos:
            xpos = node.xpos()

        if ypos is None:
            ypos = node.ypos()
        elif node.ypos() > ypos:
            ypos = node.ypos()

    # Default to (0, 0)
    if xpos is None:
        xpos = 0
    if ypos is None:
        ypos = 0

    return xpos, ypos


def upper_left_pos(nodes=None):
    """
    Get furthest upper left position by a node

    Args:
        nodes (list of nuke.Node): List of nodes to compare
                                   Defaults to all ungrouped nodes

    Returns:
        x_pos, y_pos
    """
    nodes = nodes or get_all_nodes(groups=False)

    xpos = None
    ypos = None

    for node in nodes:
        if xpos is None:
            xpos = node.xpos()
        elif node.xpos() < xpos:
            xpos = node.xpos()

        if ypos is None:
            ypos = node.ypos()
        elif node.ypos() < ypos:
            ypos = node.ypos()

    # Default to (0, 0)
    if xpos is None:
        xpos = 0
    if ypos is None:
        ypos = 0

    return xpos, ypos
